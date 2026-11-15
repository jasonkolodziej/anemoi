"""CNN / U-Net satellite feature extractor.

Scope v2.1 §3.4. Encoder front-end over GOES imagery stacks; its latent feeds
the transformer and GNN backbones and, via the latent extractor, Anemoi-Spread.
"""

from __future__ import annotations

from .base import DEFAULT_LEADS, ModelSpec, extra_input_conv, require_torch

#: Parameter-name prefixes of the steering input path: the parts Stage B
#: trains outside the head when the model reads steering.
STEERING_PARAM_PREFIXES = ("blocks.0.conv1.extra.", "blocks.0.skip.extra.")


def build_cnn(
    in_channels: int = 5,
    base_width: int = 32,
    depth: int = 4,
    latent_dim: int = 256,
    lead_hours: tuple[int, ...] = DEFAULT_LEADS,
    n_steering: int = 0,
):
    """Residual encoder over multi-channel storm-centred imagery.

    Returns ``(module, spec)``. Global average pooling at the end makes the
    encoder resolution-agnostic, which matters because GOES crop sizes differ
    between the 512 and 1024 pixel datasets in §4.3 Stage 4.

    ``n_steering`` > 0 adds that many input channels after the
    ``in_channels`` (forecast-lead steering as constant channels,
    `data.steering`; Decision Log 68). The first block's two convs that
    read the input (``conv1`` and ``skip``) each get a zero-initialised,
    bias-free conv for them (`models.base.extra_input_conv`), so the model
    computes the plain CNN until those train. With 0 (the default, and
    every version from before the steering input) nothing changes and
    older checkpoints load unchanged.
    """
    torch = require_torch()
    nn = torch.nn

    spec = ModelSpec(
        name="cnn", input_dim=in_channels + n_steering, latent_dim=latent_dim,
        lead_hours=lead_hours,
    )

    class ResBlock(nn.Module):
        def __init__(self, c_in: int, c_out: int) -> None:
            super().__init__()
            self.conv1 = nn.Conv2d(c_in, c_out, 3, stride=2, padding=1)
            self.norm1 = nn.GroupNorm(8, c_out)
            self.conv2 = nn.Conv2d(c_out, c_out, 3, padding=1)
            self.norm2 = nn.GroupNorm(8, c_out)
            self.skip = nn.Conv2d(c_in, c_out, 1, stride=2)
            self.act = nn.GELU()

        def forward(self, x):
            h = self.act(self.norm1(self.conv1(x)))
            h = self.norm2(self.conv2(h))
            return self.act(h + self.skip(x))

    class StormCNN(nn.Module):
        def __init__(self) -> None:
            super().__init__()
            widths = [in_channels] + [base_width * (2**i) for i in range(depth)]
            self.blocks = nn.Sequential(
                *[ResBlock(widths[i], widths[i + 1]) for i in range(depth)]
            )
            if n_steering:
                first = self.blocks[0]
                first.conv1 = extra_input_conv(first.conv1, n_steering)
                first.skip = extra_input_conv(first.skip, n_steering)
            self.pool = nn.AdaptiveAvgPool2d(1)
            self.project = nn.Linear(widths[-1], latent_dim)
            self.head = nn.Sequential(
                nn.Linear(latent_dim, latent_dim // 2),
                nn.GELU(),
                nn.Linear(latent_dim // 2, spec.output_dim),
            )

        def encode(self, x):
            h = self.blocks(x)
            return self.project(self.pool(h).flatten(1))

        def forward(self, x):
            latent = self.encode(x)
            return self.head(latent).view(-1, len(lead_hours), spec.outputs_per_lead)

    return StormCNN(), spec
