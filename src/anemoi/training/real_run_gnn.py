"""Real Stage A/B curriculum run for the GNN baseline, against cached real
GriddedFields (#22).

`models.gnn.build_gnn`'s docstring frames the intended real input as
"station networks, buoy arrays, icosahedral mesh points" -- an irregular
mesh this project has no real source for yet (`ndbc`/`dropsonde`/
`microwave` aren't fetched for real). What real data this project does
have is the same cached `GriddedFields` CNN/Transformer use: a *regular*
grid, not an irregular mesh, but real, storm-centred, and multi-field --
close enough in shape to exercise real message passing honestly, if that
grid is treated as a lattice graph rather than resampled onto a fake
irregular mesh.

Design, all driven by `GNN_STRIDE`/the cached shape (no arbitrary choices
free-floating from the real data):

- **Nodes**: the cached grid subsampled every `GNN_STRIDE` cells in each
  direction (dense per-pixel nodes -- 1600+ for a 40x40 crop -- would make
  message passing expensive for little benefit at this box size). Each
  node's features are the 10 cached fields' values at that cell plus its
  (row, col) offset from the grid centre in cells -- 12 features, matching
  `build_gnn`'s own `node_features=12` default exactly.
- **Edges**: 4-connectivity between lattice-adjacent subsampled nodes
  (bidirectional). Edge features are (d_row, d_col, distance) in cells --
  3 features, matching `edge_features=3` exactly.
- **Center node**: the node nearest the grid's centre -- the storm's own
  position, since `GriddedFields` are already storm-centred.

The lattice topology (edge_index/edge_attr/center) is identical for every
sample built from the same cached shape/stride, so it's computed once and
reused, and batched across samples the standard block-diagonal way
(concatenate node blocks, offset each sample's edge indices by its block
start) rather than looping one graph at a time -- `build_gnn`'s own
docstring notes it's `index_add_`-based specifically so this works without
a PyG dependency.
"""

from __future__ import annotations

import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from ..data.besttrack import Track, WorkingTrackNoise
from ..data.features import sanitize_field_pixels
from ..data.gridded_cache import FetchTask, cache_path, load_cached_fields
from ..data.sources import Flavor
from ..data.splits import Split, assign_splits, filter_tracks
from ..metrics.track import ForecastPoint, VerificationPair, to_metric_dict, verify
from ..models.base import DEFAULT_LEADS, require_torch
from ..tracking.checkpoint_store import CheckpointStore
from .curriculum import Curriculum, CurriculumRun, StageResult, StageSpec
from .device import get_device
from .promotion import MetricSet
from .real_run import (
    LEAD_STEPS,
    RunArtifacts,
    boundaries_for_flavor,
    displacement_to_latlon,
    freeze_encoder,
    iter_stage_windows,
)

GNN_FIELD_NAMES: tuple[str, ...] = (
    "u200", "v200", "u850", "v850", "z500", "rh700", "t700", "mslp", "sst", "ohc",
)
#: Subsample the cached grid every this many cells per side -- keeps the
#: mesh a few hundred nodes rather than a few thousand.
GNN_STRIDE = 4
NODE_FEATURES = len(GNN_FIELD_NAMES) + 2  # + (row_offset, col_offset)
EDGE_FEATURES = 3  # (d_row, d_col, distance), all in cells


@dataclass(frozen=True, slots=True)
class MeshTopology:
    """Lattice graph structure for one cached-field shape/stride -- the
    same for every sample built from that shape, so built once."""

    n_nodes: int
    edge_index: np.ndarray  # (2, n_edges)
    edge_attr: np.ndarray  # (n_edges, EDGE_FEATURES)
    center_index: int
    rows: tuple
    cols: tuple


def build_mesh_topology(shape: tuple[int, int], stride: int = GNN_STRIDE) -> MeshTopology:
    h, w = shape
    rows = tuple(range(0, h, stride))
    cols = tuple(range(0, w, stride))
    nh, nw = len(rows), len(cols)

    def node_id(r: int, c: int) -> int:
        return r * nw + c

    src: list[int] = []
    dst: list[int] = []
    attrs: list[list[float]] = []
    for r in range(nh):
        for c in range(nw):
            nid = node_id(r, c)
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = r + dr, c + dc
                if 0 <= nr < nh and 0 <= nc < nw:
                    src.append(nid)
                    dst.append(node_id(nr, nc))
                    attrs.append([float(dr), float(dc), float(np.hypot(dr, dc))])

    center_index = node_id(nh // 2, nw // 2)
    return MeshTopology(
        n_nodes=nh * nw,
        edge_index=np.array([src, dst], dtype=np.int64),
        edge_attr=np.array(attrs, dtype=np.float32),
        center_index=center_index,
        rows=rows,
        cols=cols,
    )


def _node_features(fields, topo: MeshTopology) -> np.ndarray | None:
    """(n_nodes, NODE_FEATURES) for one sample's cached fields, or ``None``
    if any of `GNN_FIELD_NAMES` (real ERA5 ``sst``/``ohc`` are NaN over
    land) is entirely NaN for this window -- the caller must skip it, the
    same contract `real_run_cnn._sanitized_channel_stack`/`real_run_
    transformer._sanitized_channel_stack` use. Each field is sanitized via
    `data.features.sanitize_field_pixels` (NaN pixels filled with that
    field's own real spatial mean) once per channel, *before* the per-node
    ``[row, col]`` lookup below, so a land node reads a real value instead
    of NaN -- see that function's docstring for why an unhandled NaN here
    would otherwise corrupt this whole stage's online standardization
    statistics, not just this one window."""
    nh, nw = len(topo.rows), len(topo.cols)
    crow, ccol = topo.rows[nh // 2], topo.cols[nw // 2]
    sanitized: dict[str, np.ndarray] = {}
    for name in GNN_FIELD_NAMES:
        field = sanitize_field_pixels(getattr(fields, name))
        if field is None:
            return None
        sanitized[name] = field
    out = np.empty((topo.n_nodes, NODE_FEATURES), dtype=np.float32)
    for r, row in enumerate(topo.rows):
        for c, col in enumerate(topo.cols):
            nid = r * nw + c
            values = [sanitized[name][row, col] for name in GNN_FIELD_NAMES]
            out[nid, : len(GNN_FIELD_NAMES)] = values
            out[nid, len(GNN_FIELD_NAMES)] = row - crow
            out[nid, len(GNN_FIELD_NAMES) + 1] = col - ccol
    return out


@dataclass(frozen=True, slots=True)
class GnnStageSamples:
    x: np.ndarray  # (N, n_nodes, NODE_FEATURES)
    y: np.ndarray
    mask: np.ndarray
    base_lat: np.ndarray
    base_lon: np.ndarray
    topology: MeshTopology | None

    def __len__(self) -> int:
        return len(self.x)


def build_gnn_samples(
    tracks: list[Track],
    cache_dir: Path | str,
    rng: np.random.Generator,
    n_augment: int = 1,
    noise: WorkingTrackNoise | None = None,
    stride: int = GNN_STRIDE,
) -> GnnStageSamples:
    """Same windows/targets as `real_run.build_stage_samples`; ``x`` is a
    lattice-graph node-feature block built from the real cached
    `GriddedFields` (see module docstring). A fix with no cached file yet
    is skipped. All samples must share one cached shape (same as
    `real_run_cnn`'s ragged-shape check) since the topology is shared."""
    cache_dir = Path(cache_dir)
    x_rows: list[np.ndarray] = []
    y_rows: list[np.ndarray] = []
    mask_rows: list[np.ndarray] = []
    base_lat_rows: list[float] = []
    base_lon_rows: list[float] = []
    topo: MeshTopology | None = None
    shape: tuple[int, int] | None = None

    for sw in iter_stage_windows(tracks, rng, n_augment, noise):
        task = FetchTask(
            storm_id=sw.storm_id, valid_time=sw.current.valid_time,
            lat=sw.current.lat, lon=sw.current.lon,
        )
        path = cache_path(cache_dir, task)
        if not path.exists():
            continue
        fields = load_cached_fields(path)
        field_shape = fields.shape
        if shape is None:
            shape = field_shape
            topo = build_mesh_topology(shape, stride)
        elif field_shape != shape:
            raise ValueError(
                f"ragged cached field shape for {sw.storm_id}: {field_shape} != {shape} "
                "-- cache was built with inconsistent box_deg"
            )

        node_features = _node_features(fields, topo)
        if node_features is None:
            continue
        x_rows.append(node_features)
        y_rows.append(sw.y)
        mask_rows.append(sw.mask)
        base_lat_rows.append(sw.current.lat)
        base_lon_rows.append(sw.current.lon)

    n_leads = len(LEAD_STEPS)
    if not x_rows:
        return GnnStageSamples(
            x=np.empty((0, 0, NODE_FEATURES)),
            y=np.empty((0, n_leads, 3)),
            mask=np.empty((0, n_leads), dtype=bool),
            base_lat=np.empty((0,)),
            base_lon=np.empty((0,)),
            topology=None,
        )
    return GnnStageSamples(
        x=np.stack(x_rows),
        y=np.stack(y_rows),
        mask=np.stack(mask_rows),
        base_lat=np.array(base_lat_rows),
        base_lon=np.array(base_lon_rows),
        topology=topo,
    )


def batch_graph(
    x: np.ndarray, topo: MeshTopology
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Block-diagonal batch of ``len(x)`` copies of ``topo``'s graph: one
    big disjoint graph whose message passing never crosses between
    samples, plus per-sample center-node indices into it (`build_gnn`'s
    ``forward`` accepts ``center_index`` as an int OR an index array, so
    ``h[center_index]`` fancy-indexes out one row per sample)."""
    n_samples, n_nodes, _ = x.shape
    x_flat = x.reshape(n_samples * n_nodes, x.shape[-1])
    offsets = (np.arange(n_samples) * n_nodes)[:, None, None]
    edge_index = (topo.edge_index[None, :, :] + offsets).transpose(1, 0, 2)
    edge_index = edge_index.reshape(2, -1)
    edge_attr = np.tile(topo.edge_attr, (n_samples, 1))
    center_indices = np.arange(n_samples) * n_nodes + topo.center_index
    return x_flat, edge_index, edge_attr, center_indices


def _standardize_x(x: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    mean = x.mean(axis=(0, 1), keepdims=True)
    std = x.std(axis=(0, 1), keepdims=True)
    std[std < 1e-8] = 1.0
    return (x - mean) / std, mean, std


def _standardize_y(y: np.ndarray, mask: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    n_leads = y.shape[1]
    mean = np.zeros((n_leads, 3))
    std = np.ones((n_leads, 3))
    for li in range(n_leads):
        valid = mask[:, li]
        if valid.any():
            vals = y[valid, li, :]
            mean[li] = vals.mean(axis=0)
            s = vals.std(axis=0)
            s[s < 1e-8] = 1.0
            std[li] = s
    return mean, std


def train_gnn_stage(
    model,
    stage: StageSpec,
    train_tracks: list[Track],
    val_tracks: list[Track],
    cache_dir: Path | str,
    rng: np.random.Generator,
    *,
    n_augment: int = 3,
    device=None,
) -> tuple[object, float, float, MetricSet, tuple]:
    """GNN analog of `real_run.train_lstm_stage` -- see that function for
    the loss/verification design this mirrors, including the extra
    ``(x_mean, x_std, y_mean, y_std)`` returned alongside the usual four
    values. ``x`` is batched via `batch_graph` (block-diagonal, see module
    docstring) before each forward pass."""
    if not train_tracks or not val_tracks:
        raise ValueError(f"stage {stage.name}: empty train or val storm set")

    torch = require_torch()
    device = device or get_device()

    train_samples = build_gnn_samples(train_tracks, cache_dir, rng, n_augment=n_augment)
    val_samples = build_gnn_samples(val_tracks, cache_dir, rng, n_augment=1)
    if len(train_samples) == 0 or len(val_samples) == 0:
        raise ValueError(
            f"stage {stage.name}: no cached GriddedFields matched the given tracks in "
            f"{cache_dir} -- has data.era5_cache/data.gdas_cache fetched anything yet?"
        )

    x_train, x_mean, x_std = _standardize_x(train_samples.x)
    y_mean, y_std = _standardize_y(train_samples.y, train_samples.mask)
    x_val = (val_samples.x - x_mean) / x_std
    y_train_z = (train_samples.y - y_mean) / y_std
    y_val_z = (val_samples.y - y_mean) / y_std

    freeze_encoder(model, stage.frozen_modules)
    model.to(device)

    def masked_mse(pred, target, mask3):
        diff2 = (pred - target) ** 2 * mask3
        return diff2.sum() / mask3.sum().clamp(min=1.0)

    xt_np, ei_train, ea_train, ci_train = batch_graph(x_train, train_samples.topology)
    xt = torch.as_tensor(xt_np, dtype=torch.float32, device=device)
    ei_t = torch.as_tensor(ei_train, dtype=torch.long, device=device)
    ea_t = torch.as_tensor(ea_train, dtype=torch.float32, device=device)
    ci_t = torch.as_tensor(ci_train, dtype=torch.long, device=device)
    yt = torch.as_tensor(y_train_z, dtype=torch.float32, device=device)
    mt = torch.as_tensor(train_samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)

    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.Adam(trainable, lr=stage.learning_rate)

    model.train()
    for _ in range(stage.epochs):
        opt.zero_grad()
        pred = model(xt, ei_t, ea_t, center_index=ci_t)
        loss = masked_mse(pred, yt, mt)
        loss.backward()
        opt.step()

    model.eval()
    with torch.no_grad():
        train_loss = float(masked_mse(model(xt, ei_t, ea_t, center_index=ci_t), yt, mt).item())

        xv_np, ei_val, ea_val, ci_val = batch_graph(x_val, val_samples.topology)
        xv = torch.as_tensor(xv_np, dtype=torch.float32, device=device)
        ei_v = torch.as_tensor(ei_val, dtype=torch.long, device=device)
        ea_v = torch.as_tensor(ea_val, dtype=torch.float32, device=device)
        ci_v = torch.as_tensor(ci_val, dtype=torch.long, device=device)
        yv = torch.as_tensor(y_val_z, dtype=torch.float32, device=device)
        mv = torch.as_tensor(val_samples.mask, dtype=torch.float32, device=device).unsqueeze(-1)
        pred_val_z = model(xv, ei_v, ea_v, center_index=ci_v)
        val_loss = float(masked_mse(pred_val_z, yv, mv).item())
        pred_val = pred_val_z.cpu().numpy() * y_std + y_mean

    pairs: list[VerificationPair] = []
    for si in range(len(val_samples)):
        base_lat, base_lon = val_samples.base_lat[si], val_samples.base_lon[si]
        for li, lead_hours in enumerate(DEFAULT_LEADS):
            if not val_samples.mask[si, li]:
                continue
            pred_dx, pred_dy, pred_wind = pred_val[si, li]
            pred_lat, pred_lon = displacement_to_latlon(base_lat, base_lon, pred_dx, pred_dy)
            obs_dx, obs_dy, obs_wind = val_samples.y[si, li]
            obs_lat, obs_lon = displacement_to_latlon(base_lat, base_lon, obs_dx, obs_dy)
            pairs.append(
                VerificationPair(
                    forecast=ForecastPoint(
                        lead_hours=lead_hours, lat=pred_lat, lon=pred_lon,
                        max_wind_kt=float(pred_wind),
                    ),
                    obs_lat=obs_lat,
                    obs_lon=obs_lon,
                    obs_wind_kt=float(obs_wind),
                )
            )

    if not pairs:
        raise ValueError(f"stage {stage.name}: no verifiable (lead, sample) pairs in val")
    val_metrics = MetricSet(split="val", flavor=stage.flavor, values=to_metric_dict(verify(pairs)))
    return model, train_loss, val_loss, val_metrics, (x_mean, x_std, y_mean, y_std)


def train_gnn_stage_streaming(
    model,
    stage: StageSpec,
    train_tracks: list[Track],
    val_tracks: list[Track],
    cache_dir: Path | str,
    rng: np.random.Generator,
    *,
    n_augment: int = 3,
    batch_size: int = 32,
    num_workers: int = 0,
    stride: int = GNN_STRIDE,
    device=None,
) -> tuple[object, float, float, MetricSet, tuple]:
    """`train_gnn_stage`'s streaming analog (`docs/streaming_dataloader.md`) --
    same return contract, real per-batch training via a `torch.utils.data
    .DataLoader` and online standardisation statistics instead of one
    full-dataset GPU tensor. See `real_run_cnn.train_cnn_stage_streaming`
    for the reference this follows; the one GNN-specific piece is the
    shared `MeshTopology` (module docstring) -- built once, lazily, the
    first time any window's cached fields are loaded (during the stats-
    fitting pass, which visits every window in order before training
    starts), then reused to `batch_graph` each `DataLoader` batch right
    before the forward pass, same as the full-batch path does for the
    whole dataset at once. ``num_workers`` (default 0) forwards to
    `streaming.make_dataloader` -- safe here specifically because the
    stats-fitting pass (which populates `mesh_state`, `build_x`'s lazily-
    built topology cache) always runs synchronously in the main process
    *before* `train_loader`/`val_loader` are constructed, so every forked
    worker process inherits an already-populated topology via
    copy-on-write, never a race to build it themselves.
    """
    from .streaming import (
        OnlineMaskedLeadMeanStd,
        OnlineMeanStd,
        WindowDataset,
        filter_windows_with_cache,
        filter_windows_with_finite_fields,
        make_dataloader,
    )

    if not train_tracks or not val_tracks:
        raise ValueError(f"stage {stage.name}: empty train or val storm set")

    torch = require_torch()
    device = device or get_device()

    raw_train_windows = filter_windows_with_cache(
        list(iter_stage_windows(train_tracks, rng, n_augment)), cache_dir,
    )
    train_windows = filter_windows_with_finite_fields(raw_train_windows, cache_dir, GNN_FIELD_NAMES)
    raw_val_windows = filter_windows_with_cache(
        list(iter_stage_windows(val_tracks, rng, 1)), cache_dir,
    )
    val_windows = filter_windows_with_finite_fields(raw_val_windows, cache_dir, GNN_FIELD_NAMES)
    if not train_windows or not val_windows:
        raise ValueError(
            f"stage {stage.name}: no cached GriddedFields matched the given tracks in "
            f"{cache_dir} -- has data.era5_cache/data.gdas_cache fetched anything yet, or "
            "were every matched window's fields entirely NaN (storms entirely over land)?"
        )

    cache_dir = Path(cache_dir)
    mesh_state: dict[str, object] = {"topo": None, "shape": None}

    def build_x(sw):
        fields = load_cached_fields(cache_path(cache_dir, FetchTask(
            storm_id=sw.storm_id, valid_time=sw.current.valid_time,
            lat=sw.current.lat, lon=sw.current.lon,
        )))
        if mesh_state["shape"] is None:
            mesh_state["shape"] = fields.shape
            mesh_state["topo"] = build_mesh_topology(fields.shape, stride)
        elif fields.shape != mesh_state["shape"]:
            raise ValueError(
                f"ragged cached field shape for {sw.storm_id}: {fields.shape} != "
                f"{mesh_state['shape']} -- cache was built with inconsistent box_deg"
            )
        return _node_features(fields, mesh_state["topo"])

    n_leads = len(LEAD_STEPS)
    raw_train_ds = WindowDataset(train_windows, build_x)
    x_acc = OnlineMeanStd(reduce_axes=(0, 1), keepdims=True)
    y_acc = OnlineMaskedLeadMeanStd(n_leads=n_leads)
    for i in range(len(raw_train_ds)):
        x, y, mask = raw_train_ds[i]
        x_acc.update(x[None])
        y_acc.update(y[None], mask[None].astype(bool))
    x_mean, x_std = x_acc.finalize()
    y_mean, y_std = y_acc.finalize()
    # x_mean/x_std keep the (1, 1, F) shape _standardize_x's callers expect
    # against a *batched* (N, n_nodes, F) array (see real_run_cnn's same
    # fix for why); WindowDataset standardizes one *unbatched* (n_nodes, F)
    # item at a time, so it needs the leading batch axis squeezed off.
    item_x_mean, item_x_std = x_mean[0], x_std[0]
    topo = mesh_state["topo"]
    assert topo is not None  # set by build_x on the fitting pass above

    train_ds = WindowDataset(
        train_windows, build_x, x_mean=item_x_mean, x_std=item_x_std, y_mean=y_mean, y_std=y_std,
    )
    val_ds = WindowDataset(
        val_windows, build_x, x_mean=item_x_mean, x_std=item_x_std, y_mean=y_mean, y_std=y_std,
    )

    def collate(batch):
        xs, ys, masks = zip(*batch, strict=True)
        return np.stack(xs), np.stack(ys), np.stack(masks)

    train_loader = make_dataloader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=num_workers, collate_fn=collate,
    )
    val_loader = make_dataloader(
        val_ds, batch_size=batch_size, shuffle=False, num_workers=num_workers, collate_fn=collate,
    )

    freeze_encoder(model, stage.frozen_modules)
    model.to(device)

    def masked_mse_sums(pred, target, mask3):
        diff2 = (pred - target) ** 2 * mask3
        return diff2.sum(), mask3.sum()

    def forward_batch(xb_np: np.ndarray):
        xf, ei, ea, ci = batch_graph(xb_np, topo)
        xf_t = torch.as_tensor(xf, dtype=torch.float32, device=device)
        ei_t = torch.as_tensor(ei, dtype=torch.long, device=device)
        ea_t = torch.as_tensor(ea, dtype=torch.float32, device=device)
        ci_t = torch.as_tensor(ci, dtype=torch.long, device=device)
        return model(xf_t, ei_t, ea_t, center_index=ci_t)

    trainable = [p for p in model.parameters() if p.requires_grad]
    opt = torch.optim.Adam(trainable, lr=stage.learning_rate)

    model.train()
    for _ in range(stage.epochs):
        for xb, yb, mb in train_loader:
            yt = torch.as_tensor(yb, dtype=torch.float32, device=device)
            mt = torch.as_tensor(mb, dtype=torch.float32, device=device).unsqueeze(-1)
            opt.zero_grad()
            diff2_sum, mask_sum = masked_mse_sums(forward_batch(xb), yt, mt)
            loss = diff2_sum / mask_sum.clamp(min=1.0)
            loss.backward()
            opt.step()

    model.eval()
    with torch.no_grad():
        train_diff2, train_mask = 0.0, 0.0
        for xb, yb, mb in train_loader:
            yt = torch.as_tensor(yb, dtype=torch.float32, device=device)
            mt = torch.as_tensor(mb, dtype=torch.float32, device=device).unsqueeze(-1)
            d, m = masked_mse_sums(forward_batch(xb), yt, mt)
            train_diff2 += float(d.item())
            train_mask += float(m.item())
        train_loss = train_diff2 / max(train_mask, 1.0)

        val_diff2, val_mask = 0.0, 0.0
        pred_val_rows: list[np.ndarray] = []
        for xb, yb, mb in val_loader:
            yt = torch.as_tensor(yb, dtype=torch.float32, device=device)
            mt = torch.as_tensor(mb, dtype=torch.float32, device=device).unsqueeze(-1)
            pred = forward_batch(xb)
            d, m = masked_mse_sums(pred, yt, mt)
            val_diff2 += float(d.item())
            val_mask += float(m.item())
            pred_val_rows.append(pred.cpu().numpy())
        val_loss = val_diff2 / max(val_mask, 1.0)
        pred_val = np.concatenate(pred_val_rows, axis=0) * y_std + y_mean

    pairs: list[VerificationPair] = []
    for si, sw in enumerate(val_windows):
        base_lat, base_lon = sw.current.lat, sw.current.lon
        for li, lead_hours in enumerate(DEFAULT_LEADS):
            if not sw.mask[li]:
                continue
            pred_dx, pred_dy, pred_wind = pred_val[si, li]
            pred_lat, pred_lon = displacement_to_latlon(base_lat, base_lon, pred_dx, pred_dy)
            obs_dx, obs_dy, obs_wind = sw.y[li]
            obs_lat, obs_lon = displacement_to_latlon(base_lat, base_lon, obs_dx, obs_dy)
            pairs.append(
                VerificationPair(
                    forecast=ForecastPoint(
                        lead_hours=lead_hours, lat=pred_lat, lon=pred_lon,
                        max_wind_kt=float(pred_wind),
                    ),
                    obs_lat=obs_lat,
                    obs_lon=obs_lon,
                    obs_wind_kt=float(obs_wind),
                )
            )

    if not pairs:
        raise ValueError(f"stage {stage.name}: no verifiable (lead, sample) pairs in val")
    val_metrics = MetricSet(split="val", flavor=stage.flavor, values=to_metric_dict(verify(pairs)))
    return model, train_loss, val_loss, val_metrics, (x_mean, x_std, y_mean, y_std)


def run_gnn_curriculum(
    tracks: list[Track],
    checkpoint_store: CheckpointStore,
    era5_cache_dir: Path | str,
    gdas_cache_dir: Path | str,
    *,
    seed: int = 20260806,
    n_augment: int = 3,
    hidden_dim: int = 128,
    curriculum_kwargs: dict | None = None,
    streaming: bool = False,
    batch_size: int = 32,
    num_workers: int = 0,
) -> tuple[CurriculumRun, MetricSet, RunArtifacts]:
    """Run the real Stage A -> Stage B curriculum for the GNN baseline
    against real cached GriddedFields, treated as a lattice mesh (see
    module docstring). Also returns a ``RunArtifacts`` bundling the
    trained Stage B model with its standardisation stats (see
    `real_run.run_lstm_curriculum`'s docstring for why) -- its mesh
    topology isn't included since `build_mesh_topology` is a pure function
    of the cached field shape/stride, cheap to rebuild rather than thread
    through.

    ``streaming=True`` uses `train_gnn_stage_streaming` instead of the
    default full-batch `train_gnn_stage` (`docs/streaming_dataloader.md`).
    ``num_workers`` (streaming only, default 0) forwards to
    `streaming.make_dataloader` -- see that function's docstring.
    """
    from ..models.gnn import build_gnn

    require_torch()
    rng = np.random.default_rng(seed)
    curriculum = Curriculum.standard("gnn", **(curriculum_kwargs or {}))
    run = CurriculumRun(curriculum=curriculum)

    model = None
    val_metrics: MetricSet | None = None
    for stage in curriculum.stages:
        cache_dir = era5_cache_dir if stage.flavor is Flavor.ERA5_PRETRAIN else gdas_cache_dir
        boundaries = boundaries_for_flavor(stage.flavor)
        assignment = assign_splits(tracks, boundaries)
        train_tracks = filter_tracks(tracks, assignment, Split.TRAIN)
        val_tracks = filter_tracks(tracks, assignment, Split.VAL)

        if model is None:
            model, _spec = build_gnn(
                node_features=NODE_FEATURES, edge_features=EDGE_FEATURES,
                hidden_dim=hidden_dim, lead_hours=DEFAULT_LEADS,
            )

        stage_fn = train_gnn_stage_streaming if streaming else train_gnn_stage
        stage_kwargs = {"batch_size": batch_size, "num_workers": num_workers} if streaming else {}
        model, train_loss, val_loss, val_metrics, stats = stage_fn(
            model, stage, train_tracks, val_tracks, cache_dir, rng,
            n_augment=n_augment, **stage_kwargs,
        )

        torch = require_torch()
        with tempfile.TemporaryDirectory() as tmpdir:
            local_path = Path(tmpdir) / f"{stage.name}.pt"
            torch.save(model.state_dict(), local_path)
            key = f"checkpoints/gnn/{stage.name}/{datetime.now(UTC):%Y%m%dT%H%M%S}.pt"
            checkpoint_uri = checkpoint_store.upload(local_path, key)

        run.record(
            StageResult(
                stage_name=stage.name,
                flavor=stage.flavor,
                epochs_completed=stage.epochs,
                final_train_loss=train_loss,
                final_val_loss=val_loss,
                checkpoint_uri=checkpoint_uri,
                completed_at=datetime.now(UTC),
            )
        )

    assert val_metrics is not None
    x_mean, x_std, y_mean, y_std = stats
    artifacts = RunArtifacts(model=model, x_mean=x_mean, x_std=x_std, y_mean=y_mean, y_std=y_std)
    return run, val_metrics, artifacts
