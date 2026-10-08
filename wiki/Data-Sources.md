# Data Sources

Scope v2.1 §4.1. Implemented as `src/anemoi/data/sources.py`.

Every source carries an explicit **real-time latency** and a **role**. The inference schedule is derived from the latency column, not from assumed availability — that derivation is what v2 got wrong. See [Inference Cycle](Inference-Cycle).

---

## Roles

The role is load-bearing, not documentation. `operational_sources()` is what the inference scheduler is allowed to read, and `assert_not_operational()` is the guard that keeps reanalysis out of the production path.

| Role | Meaning |
|---|---|
| `OPERATIONAL` | Read live during a forecast cycle, and used for Stage B fine-tuning |
| `PRETRAIN_ONLY` | Stage A pretraining only. **Never** read during a cycle |
| `LABELS_ONLY` | Supervision targets and verification. **Never** a model input |

```python
from anemoi.data import sources
sources.assert_not_operational("era5")
# OperationalUseError: source 'era5' has role 'pretrain_only' and must not be
# read during a forecast cycle (Scope v2.1 §4.6). Use the operational
# equivalent: gdas_gfs
```

---

## Registry

| Source | Provider | Latency | Role | Format | Retention |
|---|---|---|---|---|---|
| `besttrack_working` | [NHC ATCF (a-/b-deck, TC-Vitals)](https://ftp.nhc.noaa.gov/atcf/) | ~45–90 min | Operational | ATCF text | Permanent |
| `besttrack_final` | [NHC / NOAA (HURDAT2)](https://www.nhc.noaa.gov/data/hurdat/) | Post-season | **Labels only** | CSV / ATCF | Permanent |
| `gdas_gfs` | [NOAA NOMADS](https://nomads.ncep.noaa.gov) (live cycle feed); [AWS Open Data](https://registry.opendata.aws/noaa-gfs-bdp-pds/) (bulk archival mirror, byte-range GRIB2) | ~3.5–4 h | Operational | GRIB2 | 2021-01-01–present in the archival mirror (verified via direct S3 listing; no documented retention policy either way — see below) |
| `era5` | [Google ARCO-ERA5](https://cloud.google.com/storage/docs/public-datasets/era5) (Zarr, anonymous); [Copernicus CDS](https://cds.climate.copernicus.eu) (origin) | ~5 days (ERA5T) | **Pretrain only** | Zarr | Rolling 10 yr + permanent storm extracts |
| `goes` | [NOAA AWS / GCS (GOES-18/19)](https://registry.opendata.aws/noaa-goes/) | ~5–20 min | Operational | NetCDF / Zarr | Rolling 1 yr raw; permanent crops |
| `ndbc` | [NDBC buoy / C-MAN](https://www.ndbc.noaa.gov) | ~15 min–1 h | Operational | JSON / NetCDF | Rolling 3 yr |
| `dropsonde` | [NOAA / AFRC](ftp://ftp.aoml.noaa.gov/hrd/pub/data/dropsonde) Live/ongoing (anonymous FTP, no registration): operationally-processed, high-res GPS dropwindsonde data from NOAA and USAF 53rd Weather Reconnaissance Squadron hurricane-season flights, organized by year/storm folder (e.g. HURR03/operproc/). | Event-driven, 1–3 h | Operational (opportunistic) | BUFR / NetCDF | Permanent |
| `microwave` | [RSS / CIMSS](ftp://ftp.remss.com) | 1–4 h, orbit-dependent | Operational (opportunistic) | HDF5 | Rolling 2 yr + permanent crops |
| `sst_ohc` | NOAA / Copernicus | ~1 day | Operational | NetCDF | Rolling 5 yr |
| `ensemble_perturbations` | GEFS / ECMWF EPS | ~4–6 h | Operational | GRIB2 | Rolling 1 yr |

**Retention note.** Raw imagery retention stays rolling for cost, but storm-relative crops are retained permanently so the CNN training archive grows beyond the rolling window. This reconciles the retention policy with the multi-decade splits — v2's 1-year GOES retention contradicted its own 1980–2025 training plan.

**`gdas_gfs`'s retention is a real, verified correction, not a rounding error.** An earlier version of this table (and `data/sources.py`) claimed GDAS was archived from 2015. Checked directly against `noaa-gfs-bdp-pds` (S3 `list-type=2` listing, 2026-09-16): real coverage starts 2021-01-01. `configs/curriculum.yaml`'s old `stage_b.season_range: [2015, 2019]` covered a period with zero real data as a result — every fix in it 404'd. No retention policy is documented for this bucket in either direction (AWS's Open Data Registry page, its YAML, and NOAA's general Big Data Program FAQ all say retention "varies by dataset," with no bucket-specific statement); don't confuse it with the older, Unidata-maintained `noaa-gfs-pds`, which *does* document an explicit rolling 4-week window — that policy is for a different bucket than this project reads from.

Given the undocumented retention, the project does not depend on NOAA's live bucket as the system of record for Stage B: `data.gdas_cache.run_fetch_cache` now filters out fixes before `GDAS_ARCHIVE_START` (2021-01-01) by default, `stage_b.season_range` is corrected to `[2021, 2023]`, and `anemoi gdas-cache --sync-archive` backfills the fetch cache into the same durable R2 bucket `tracking.checkpoint_store` uses — see [Training Architecture](Training-Architecture)'s "Durable archive" section.

---

## Implementation status

Being in the registry above means a source is *declared* -- role, latency, format all real -- not that it's *fetched* for real. As of 2026-09-22:

| Source | Real fetch implemented? |
|---|---|
| `besttrack_working` | Yes -- `data.live_atcf` / `data.atcf` |
| `besttrack_final` | Yes -- `data.hurdat2` |
| `gdas_gfs` | Yes -- `data.real_gridded` / `data.gdas_cache` |
| `era5` | Yes -- `data.real_gridded` / `data.era5_cache` |
| `goes` | Yes (2026-09-22) -- `data.real_goes` (GOES-18/19 ABI: CMIPF for IR/WV/VIS, SSTF for SST, RRQPEF for rain rate) |
| `microwave` | Yes (2026-09-22) -- `data.real_microwave` (RSS SSMIS, F16/F17/F18) |
| `ndbc` | Yes (2026-09-22) -- `data.real_ndbc` (NDBC realtime2) |
| `sst_ohc` | Partial (2026-09-22) -- SST half real via `data.real_sst` (NCEI OISST v2.1); OHC half deliberately not implemented, see below |
| `ensemble_perturbations` | Yes (2026-09-22) -- `data.real_ensemble` (NOAA GEFS only; ECMWF ENS not needed) |
| `dropsonde` | Yes (2026-09-22) -- `data.real_dropsonde` (NOAA/AFRC, real BUFR decode via eccodes) |

Every real source in the registry above now has a real fetch implementation -- `sst_ohc`'s OHC half is the only deliberate exception, see below. `data.real_goes` is also the one source wired all the way to its real consumer's exact shape (`SatelliteCrop`, same channel order `models.cnn.build_cnn` expects) rather than fetch-only; every other source here is still fetch + decode only, since nothing else currently consumes those shapes -- that's real, separate future work. This is also why `real_run_gnn.py` still substitutes a lattice-graph view of cached `GriddedFields` for the GNN's intended irregular buoy/mesh input rather than reading `data.real_ndbc`/`data.real_dropsonde` directly -- see that module's own docstring.

### Candidate real endpoints, verified 2026-09-22

Checked directly (real S3 listings, live HTTP/FTP fetches, real endpoint responses -- not just documentation) before any of this becomes code, same convention as `gdas_gfs`'s AWS bucket verification above.

| Source | Provider / product | Format | Real URI | Credentials |
|---|---|---|---|---|
| `goes` | NOAA GOES-18/19 ABI (NODD) -- **implemented**, see below | NetCDF, per-channel/product | `s3://noaa-goes18/` / `s3://noaa-goes19/`, e.g. `ABI-L2-CMIPF/{yyyy}/{doy}/{hh}/OR_ABI-L2-CMIPF-M6C{ch}_G19_s..._e..._c....nc` | None -- anonymous (`aws s3 --no-sign-request`) |
| `ndbc` | NOAA NDBC buoy / C-MAN -- **implemented**, `data.real_ndbc` | Whitespace-separated text, **not JSON/NetCDF** (corrected 2026-09-22) | [`https://www.ndbc.noaa.gov/data/realtime2/{station}.txt`](https://www.ndbc.noaa.gov/data/realtime2/) (rolling 45 days, not the registry's earlier unverified "rolling 3yr") | None |
| `dropsonde` | NOAA / AFRC (HRD) -- **implemented**, `data.real_dropsonde` | Real WMO BUFR (tarred per mission), decoded via `eccodes` | [`ftp://ftp.aoml.noaa.gov/hrd/pub/data/dropsonde/HURR{yy}/operproc/{date}{letter}{mission}_BUFR.tar.gz`](ftp://ftp.aoml.noaa.gov/hrd/pub/data/dropsonde) | None -- anonymous FTP |
| `microwave` | RSS SSMIS (F16/F17/F18) -- **implemented**, see below | gzip'd raw uint8 bytemap, **not HDF5** (corrected 2026-09-22 against the real fetched format) | `ftp.remss.com` / `ftp.ssmi.com` (same server), e.g. `/ssmi/f18/bmaps_v08/y{yyyy}/m{mm}/f18_{yyyymmdd}v8.gz` | **Requires a free account** -- register at [`register.remss.com`](https://register.remss.com/). The one real exception in this table. |
| `sst_ohc` | SST: NOAA NCEI OISST v2.1 -- **implemented**, `data.real_sst`. OHC: NOAA OSPO ERDDAP -- investigated, **not implemented** (see below) | NetCDF | SST: [`.../sea-surface-temperature-optimum-interpolation/v2.1/access/avhrr/{yyyymm}/oisst-avhrr-v02r01.{yyyymmdd}_preliminary.nc`](https://www.ncei.noaa.gov/data/sea-surface-temperature-optimum-interpolation/v2.1/access/avhrr/) (~1 day lag, confirmed live). OHC: ERDDAP griddap [`erddap.aoml.noaa.gov/hdb/erddap/griddap/UOHC_2026`](https://erddap.aoml.noaa.gov/hdb/erddap/griddap/UOHC_2026.html) or `TCHP` -- **real data stops 2026-01-26**, confirmed via a real query, ~8 months stale | None |
| `ensemble_perturbations` | NOAA GEFS -- **implemented**, `data.real_ensemble`. ECMWF ENS open data -- not needed, GEFS alone covers the real conditioning use case | GRIB2 | GEFS: `s3://noaa-gefs-pds/gefs.{yyyymmdd}/{hh}/atmos/pgrb2ap5/gep{01-30}.t{hh}z.pgrb2a.0p50.f{lead}` (+ `.idx` sidecar, real archive **since 2017-01-01**, verified via direct S3 listing -- not the registry's earlier unverified "rolling 1yr"). ECMWF (unimplemented): `s3://ecmwf-forecasts/` or [`data.ecmwf.int/forecasts/{yyyymmdd}/{hh}z/ifs/0p25/enfo/...-enfo-ef.grib2`](https://data.ecmwf.int/forecasts/) (archive only since April 2024, coarser 0.25°) | None -- both anonymous |

- **RTG_SST is stale as a target** -- NCEP retired RTG_SST_HR in February 2020 (corrected below, this page previously implied it as the real SST replacement). OISST v2.1 is the current, actively-updated real product.

### Real GOES: `data.real_goes`

Implemented 2026-09-22, closing [GitHub #146](https://github.com/jasonkolodziej/anemoi/issues/146) -- the only source in this table that's wired all the way to its real consumer's exact shape (`data.satellite.SatelliteCrop`, same channel order `models.cnn.build_cnn` expects), not fetch-only like everything else here.

Five real products, one per CNN channel, each verified live (real file, real variable, real units) before writing any fetch code:

| Channel | Real product | Real variable | Real units |
|---|---|---|---|
| `ir_brightness_temp_k` | `ABI-L2-CMIPF` channel 14 | `CMI` | K (11.2 um clean LW IR window) |
| `water_vapor_brightness_temp_k` | `ABI-L2-CMIPF` channel 9 | `CMI` | K (6.9 um mid-level WV) |
| `visible_reflectance` | `ABI-L2-CMIPF` channel 2 | `CMI` | 0-1 albedo (0.64 um red visible) |
| `sst_c` | `ABI-L2-SSTF` | `SST` | K, converted to C here |
| `rain_rate_mm_hr` | `ABI-L2-RRQPEF` | `RRQPE` | mm h-1 (already real units) |

**No byte-range `.idx` trick exists for NetCDF the way GRIB2 has one** -- this page previously flagged that as an open question. Resolved: a real full-disk channel-2 file is ~430 MB, too large to download whole, so this reads lazily instead via `fsspec`'s HTTP filesystem + `h5netcdf`'s chunked HDF5 access. Confirmed live: slicing a real 64x64 storm-relative crop out of that 430 MB file transfers only ~8 MB over HTTP -- a real ~50x reduction, not a full download.

**Real geolocation, not a flat lat/lon approximation.** GOES imagery lives in the ABI Fixed Grid -- a geostationary projection, scan angles in radians from the sub-satellite point, not a regular lat/lon grid. Converting a storm's real position into the correct pixel index needs the real projection math NOAA's own `goes_imager_projection` metadata parameterises (perspective height, ellipsoid, sub-satellite longitude). Added `pyproj` as a new dependency -- safer than hand-rolling geostationary-projection trigonometry, where a subtle bug would silently misplace every crop rather than raise anything. Verified against a real active storm's real position (AL062026 "Fay") before trusting it: the projected pixel index landed on 100% real, non-missing reflectance data in the physically sane 0-1 range.

**Real `DQF` (data quality flag) is honoured, not ignored.** Every product carries one; `DQF != 0` becomes NaN rather than being silently included as good data. This mattered in practice, not just in theory: a real SST crop near an active storm came back entirely `DQF=2` (out-of-range) -- 4095 of 4096 pixels -- a real, physically plausible cloud-cover gap near a storm (SST retrieval needs clear sky), not a decode bug. Confirmed by cross-checking the real DQF values directly rather than assuming.

**Satellite selection is manual, not auto-detected by basin.** `G19` (GOES-East, sub-satellite longitude -75.0) is the real default -- this project's only trained basin is Atlantic. `G18` (GOES-West, -137.2) is available for a caller that wants Pacific coverage. No basin-based auto-selection is built, since nothing calls this with a basin yet.

**Enforced by** `tests/test_real_goes.py` -- 8 unit tests (filename-timestamp parsing, nearest-scan selection, the real geostationary projection verified against a constructed Dataset carrying the exact real projection attributes -- the sub-satellite point must project to the grid centre -- DQF masking, off-edge-crop error handling) plus 3 real network tests (live archive listing, the full 5-product pipeline, and a dual-source parity check against `data.satellite`'s synthetic ranges -- #146's own acceptance criterion).

### Real microwave: `data.real_microwave`

Implemented 2026-09-22 against real RSS SSMIS data (DMSP F16/F17/F18). RSS's anonymous FTP access is discontinued (`220 Anonymous access discontinued. See www.remss.com/register`, confirmed live) -- a real account is required (`RSS_FTP_USERNAME`/`RSS_FTP_PASSWORD`, see `example.env`).

**Two RSS products exist under `/ssmi` and `/TC-winds` -- only one was implemented, deliberately:**

- **`/TC-winds`** is a storm-specific "fix" product (ATCF-fix-format-derived: basin, cyclone number, timestamp, sensor, lat/lon, then a wind-radii block). Confirmed live against real currently-active storms (a real SMAP fix for `EP172026` matched the live API's own lat/lon almost exactly) -- but RSS doesn't publish a column-by-column table anywhere findable, and guessing at them risked mislabelling real data as something it isn't. **Not implemented** for this reason. Update 2026-09-22: RSS's own docs ([`remss.com/missions/smap/winds/`](https://www.remss.com/missions/smap/winds/)) confirm TC-winds fixes are deliberately written "in a format easy to ingest for TC forecasts, as used in the [ATCF] systems at the US Navy" and give the 34/50/64 kt (17/25/33 m/s) wind-radii thresholds -- still no column table, but NRL's ATCF `abrdeck.html` documents `WINDCODE`/`RAD1`-`RAD4` (NE/SE/SW/NW quadrant radii, a shared ATCF convention) as a real, confirmed field group, and columns 17-21 of the real `EP172026` sample (`NEQ, 71, 0, 91, 58`) match that shape exactly. Meaningfully more confidence than before, but the leading columns between DTG and the wind-radii block (technique-number, fix-format code, position-confidence fields) are still unconfirmed -- a partial parser (well-corroborated columns only, rest left opaque) is now more defensible than before, not yet built.
- **`/ssmi/{f16,f17,f18}/bmaps_v08/`** is the raw gridded product this module reads instead: a real, fully-specified binary format, verified two independent ways before writing any parsing code -- RSS's own reference Python reader (`ftp.remss.com:/ssmi/ssmi_support/python/ssmis_daily_v7.py` + `bytemaps.py`, fetched directly) and their public documentation ([`remss.com/missions/ssmi/`](https://remss.com/missions/ssmi/), "Gridded Binary Files" section) -- both agree exactly.

**The real format**, for anyone who needs to touch this again without re-deriving it:

| | |
|---|---|
| Path | `/ssmi/{sat}/bmaps_v08/y{yyyy}/m{mm}/{sat}_{yyyymmdd}v8.gz` |
| Shape (after gunzip) | `(2, 5, 720, 1440)` uint8 -- (ascending/descending pass, variable, lat, lon) |
| Variables, in order | time (fractional GMT hour), 10m wind speed, water vapor, cloud liquid water, rain rate |
| Grid | 0.25° global; cell (0,0) centred at lat -89.875, lon 0.125 (0-360°E convention) |
| Decode | `real = byte * scale + offset` for `byte <= 250`; scale/offset per variable: time 0.1/0, wind 0.2/0, vapor 0.3/0, cloud 0.01/-0.05, rain 0.1/0 |
| Byte flags (`byte > 250`) | 251 = missing due to rain, 252 = sea ice, 253 = bad observation, 254 = no observation, 255 = land -- this module masks all five to NaN rather than distinguishing them, since nothing here needs that distinction yet |

**Verified correct, not just "ran without crashing":** decoded real 2026-09-21 data end to end (physically sane wind/vapor/cloud/rain ranges), then checked real coverage density by latitude band -- 11-17% in the tropics (`-10°` to `30°`) vs ~29% at `-60°` to `-30°`, matching expected single-polar-orbiter swath geometry (narrower equatorial overlap). A zero-coverage box directly over a real active storm (`EP172026`) turned out to be a genuine same-day gap in that satellite's tropical coverage, not a decode bug.

**Deliberately scoped to fetch + decode only** -- no storm-relative crop contract the way `data.satellite` has for GOES, since no model architecture currently consumes this shape. Building one now would be inventing an interface nobody's asked for yet.

### Real ndbc, sst, ensemble, dropsonde

Implemented 2026-09-22, closing out [GitHub #147](https://github.com/jasonkolodziej/anemoi/issues/147). Same "fetch + decode only, nothing consumes this shape yet" scoping as microwave above, for all four.

- **`data.real_ndbc`** -- NDBC's real `realtime2` product, header-driven parsing (reads the actual header row for column names rather than hardcoding positions, since some station types -- confirmed live comparing a moored buoy against a C-MAN coastal station -- omit columns like wave sensors).
- **`data.real_sst`** -- NCEI OISST v2.1, a plain small (~1.5 MB/day) NetCDF fetch. Needed a real NetCDF reader the `gridded` extra never had (`xarray` alone can't open a `.nc` file without one) -- added `h5netcdf`/`h5py`, both pure-Python-wheel installs, no compiled system library the way `eccodes` needs `libeccodes`.
- **`data.real_ensemble`** -- NOAA GEFS members (`gep01`-`gep30` perturbed, `gec00` control) on AWS Open Data. Reuses `real_gridded`'s `GDAS_LEVEL_MESSAGES`/`_parse_grib2_index` directly rather than duplicating: confirmed live that GEFS's `.idx` sidecar carries the exact same messages in the identical format GDAS already reads.
- **`data.real_dropsonde`** -- NOAA/AFRC's real BUFR archive, decoded via `eccodes`' standard WMO BUFR reader (no proprietary format to reverse-engineer, unlike RSS's TC-winds below). Confirmed live: pressure is monotonically decreasing through each profile (surface-first), release timestamps exactly match their filenames. One real implementation bug hit along the way: `eccodes.codes_new_from_message` (used for GEFS/GDAS's GRIB2 bytes) turned out to be GRIB-specific under the hood and can't read BUFR directly from bytes (`"No final 7777 in message!"`) -- BUFR needs `codes_bufr_new_from_file`, which needs a real file descriptor, fixed with the same tempfile pattern GDAS's decode already uses.

**OHC investigated and deliberately not implemented.** NOAA OSPO's ERDDAP `UOHC_2026`/`TCHP` products looked completely real -- HTTP 200, real schema, units (`KJcm-2`) matching the existing `OHC_PLACEHOLDER_KJ_CM2` constant's naming exactly -- but querying their actual data showed it stops at **2026-01-26**, ~8 months stale as of this writing. Serving 8-month-old ocean heat content as "real, current" would be worse than the honest placeholder it replaces, especially for something this seasonally volatile during hurricane season. GODAS/ORAS5 remains the documented real path; its exact access point wasn't found in the time spent this pass.

---

## Real GriddedFields: `data.real_gridded`

`gdas_gfs` and `era5` above list two providers each because live-cycle access and bulk archival access are different problems with different best answers, and `data.real_gridded` only solves the second one:

- **`open_era5(valid_time)`** reads Google's ARCO-ERA5 Zarr store directly — anonymous, no CDS account, no rate limit, no GRIB parsing. This is unambiguously the most performant path for ERA5 now that it exists; the CDS/GRIB row is the origin of the data, not a recommendation to fetch through it.
- **`fetch_gdas_grib2_fields(valid_time)`** byte-range fetches only the ~7 pressure-level GRIB2 messages this system needs from NOAA's AWS Open Data mirror, using the `.idx` sidecar to avoid downloading the full ~450 MB file. **Verified before building:** checked whether a public pre-converted Zarr exists for GDAS/GFS pressure levels first — it doesn't (dynamical.org's GFS Icechunk/Zarr stores are surface/near-surface only, no 200/500/700/850 mb fields) — so GRIB2 against the archival mirror is the most performant option actually available for this source, not a default reached for out of habit.

Both map into a storm-relative `GriddedFields` via `era5_to_gridded_fields()` / `gdas_to_gridded_fields()`. Neither source carries OHC (needs an ocean reanalysis, e.g. GODAS/ORAS5, or NOAA OSPO's real ERDDAP OHC product above); GDAS's atmospheric GRIB2 file additionally has no SST (a separate NOAA product -- NCEI OISST v2.1 above, **not** RTG_SST, which NCEP retired in February 2020 and an earlier version of this line named) — both are named placeholder constants (`OHC_PLACEHOLDER_KJ_CM2`, `GDAS_SST_PLACEHOLDER_C`), not silent approximations. See [Roadmap](Roadmap) §1's Gridded fields row for what "not yet wired as the default source" means in practice.

Optional extra: `uv sync --extra gridded` (xarray, zarr, gcsfs, eccodes, requests). ERA5 needs no system package. GDAS's `eccodes` PyPI package is pure-Python *bindings* only — it does **not** bundle the compiled `libeccodes` library (an earlier version of this line claimed it did; verified wrong on both macOS and the Ubuntu 22.04 training VM, see [Training Architecture](Training-Architecture) / `docs/train_infrastructure.md`) — install it separately: `sudo apt-get install libeccodes0` on Debian/Ubuntu, `brew install eccodes` on macOS. The network-touching functions are covered by `tests/test_real_gridded.py`'s `network`-marked tests, skipped by default — set `ANEMOI_RUN_NETWORK_TESTS=1` to run them against the real endpoints.

> GOES-16/17 in v2 are superseded. GOES-18/19 are the operational pair as of 2026; the older satellites remain in the training archive.

---

## The best-track split

Two products share the name "best track" and conflating them is the leakage bug the working/final distinction exists to prevent.

| | Working (a-/b-deck, TC-Vitals) | Final (HURDAT2) |
|---|---|---|
| Available | ~45–90 min after synoptic time | After the season |
| Built from | Whatever data was on hand | Aircraft, scatterometer, satellite reanalysis |
| Quality | Noisy, quantised (0.1°, 5 kt) | Smoothed, systematically cleaner |
| Permitted use | **Model input** and Stage B fine-tune input | **Labels and verification only** |

A model trained on final-quality history and served working-quality history has been trained on a signal that does not exist at inference time.

Enforcement lives in `data/besttrack.py`:

```python
from anemoi.data.besttrack import assert_input_safe
assert_input_safe(fixes)   # raises if any fix has quality FINAL
```

`TrackQuality` has four values: `WORKING`, `FINAL`, `EMULATED` (working-quality synthesised from final for historical Stage B), and `ESTIMATED` (extrapolated because the real fix was late).

---

## Operational vs opportunistic

Availability distinguishes three tiers, because collapsing them destroys the meaning of the degradation flag.

| Tier | Sources | Absence means |
|---|---|---|
| **Required** | `besttrack_working`, `gdas_gfs` | Cycle cannot run |
| **Optional** | `goes`, `ndbc`, `sst_ohc`, `ensemble_perturbations` | Cycle degrades, flagged |
| **Opportunistic** | `dropsonde`, `microwave` | Normal. **No flag** |

Aircraft reconnaissance only flies for threatening storms, and a microwave overpass either happened in the window or did not. Flagging their routine absence would mark every cycle degraded and the flag would stop carrying information. `InputStatus.opportunistic` separates "normally missing" from "unexpectedly missing".

---

Related: [Data Pipeline](Data-Pipeline) · [Train/Serve Consistency](Train-Serve-Consistency) · [Inference Cycle](Inference-Cycle)
