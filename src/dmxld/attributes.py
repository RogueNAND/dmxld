"""Composable fixture attributes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from dmxld.color import ColorStrategy


def _to_dmx(v: float) -> int:
    return max(0, min(255, int(v * 255)))


def _to_dmx_16bit(v: float) -> tuple[int, int]:
    val = max(0, min(65535, int(v * 65535)))
    return (val >> 8, val & 0xFF)


@dataclass
class DimmerAttr:
    """Single-channel dimmer attribute."""

    name: str = "dimmer"
    fine: bool = False

    @property
    def channel_count(self) -> int:
        return 2 if self.fine else 1

    @property
    def default_value(self) -> float:
        return 0.0

    def encode(self, value: float) -> list[int]:
        if self.fine:
            coarse, fine = _to_dmx_16bit(value)
            return [coarse, fine]
        return [_to_dmx(value)]


@dataclass
class RGBAttr:
    """3-channel RGB color attribute.

    Responds to unified "color" key with automatic conversion from any color format.
    Use "raw_rgb" key to bypass conversion and set RGB values directly.
    """

    name: str = "color"
    raw_name: str = "raw_rgb"
    strategy: ColorStrategy | None = None

    @property
    def channel_count(self) -> int:
        return 3

    @property
    def default_value(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

    def convert(self, color: tuple[float, ...]) -> tuple[float, float, float]:
        """Convert any color format to RGB."""
        # If it has 4+ channels (RGBW), convert to RGB
        if len(color) >= 4:
            from dmxld.color import rgbw_to_rgb
            return rgbw_to_rgb(color[0], color[1], color[2], color[3])
        # Already RGB (or close enough)
        return (
            color[0] if len(color) > 0 else 0.0,
            color[1] if len(color) > 1 else 0.0,
            color[2] if len(color) > 2 else 0.0,
        )

    def encode(self, value: tuple[float, ...]) -> list[int]:
        return [_to_dmx(value[0]), _to_dmx(value[1]), _to_dmx(value[2])]


@dataclass
class RGBWAttr:
    """4-channel RGBW color attribute.

    Responds to unified "color" key with automatic conversion from RGB.
    Use "raw_rgbw" key to bypass conversion and set RGBW values directly.
    """

    name: str = "color"
    raw_name: str = "raw_rgbw"
    strategy: ColorStrategy | None = None

    @property
    def channel_count(self) -> int:
        return 4

    @property
    def default_value(self) -> tuple[float, float, float, float]:
        return (0.0, 0.0, 0.0, 0.0)

    def convert(self, color: tuple[float, ...]) -> tuple[float, float, float, float]:
        """Convert any color format to RGBW."""
        # If it's already RGBW (4 channels), use as-is
        if len(color) >= 4:
            return (color[0], color[1], color[2], color[3])
        # Convert RGB to RGBW
        from dmxld.color import rgb_to_rgbw
        r = color[0] if len(color) > 0 else 0.0
        g = color[1] if len(color) > 1 else 0.0
        b = color[2] if len(color) > 2 else 0.0
        return rgb_to_rgbw(r, g, b, self.strategy)

    def encode(self, value: tuple[float, ...]) -> list[int]:
        return [_to_dmx(v) for v in value[:4]]


@dataclass
class RGBAAttr:
    """4-channel RGBA (Red, Green, Blue, Amber) color attribute.

    Responds to unified "color" key with automatic conversion from RGB.
    Use "raw_rgba" key to bypass conversion and set RGBA values directly.
    """

    name: str = "color"
    raw_name: str = "raw_rgba"
    strategy: ColorStrategy | None = None

    @property
    def channel_count(self) -> int:
        return 4

    @property
    def default_value(self) -> tuple[float, float, float, float]:
        return (0.0, 0.0, 0.0, 0.0)

    def convert(self, color: tuple[float, ...]) -> tuple[float, float, float, float]:
        """Convert any color format to RGBA."""
        # If it's already 4 channels, assume it's RGBA
        if len(color) >= 4:
            return (color[0], color[1], color[2], color[3])
        # Convert RGB to RGBA
        from dmxld.color import rgb_to_rgba
        r = color[0] if len(color) > 0 else 0.0
        g = color[1] if len(color) > 1 else 0.0
        b = color[2] if len(color) > 2 else 0.0
        return rgb_to_rgba(r, g, b)

    def encode(self, value: tuple[float, ...]) -> list[int]:
        return [_to_dmx(v) for v in value[:4]]


@dataclass
class RGBAWAttr:
    """5-channel RGBAW (Red, Green, Blue, Amber, White) color attribute.

    Responds to unified "color" key with automatic conversion from RGB.
    Use "raw_rgbaw" key to bypass conversion and set RGBAW values directly.
    """

    name: str = "color"
    raw_name: str = "raw_rgbaw"
    strategy: ColorStrategy | None = None

    @property
    def channel_count(self) -> int:
        return 5

    @property
    def default_value(self) -> tuple[float, float, float, float, float]:
        return (0.0, 0.0, 0.0, 0.0, 0.0)

    def convert(
        self, color: tuple[float, ...]
    ) -> tuple[float, float, float, float, float]:
        """Convert any color format to RGBAW."""
        # If it's already 5 channels, use as-is
        if len(color) >= 5:
            return (color[0], color[1], color[2], color[3], color[4])
        # Convert from RGB: extract both amber and white
        from dmxld.color import rgb_to_rgba, rgb_to_rgbw
        r = color[0] if len(color) > 0 else 0.0
        g = color[1] if len(color) > 1 else 0.0
        b = color[2] if len(color) > 2 else 0.0

        # First extract white
        r_w, g_w, b_w, w = rgb_to_rgbw(r, g, b, self.strategy)
        # Then extract amber from remaining RGB
        r_out, g_out, b_out, a = rgb_to_rgba(r_w, g_w, b_w)

        return (r_out, g_out, b_out, a, w)

    def encode(self, value: tuple[float, ...]) -> list[int]:
        return [_to_dmx(v) for v in value[:5]]


@dataclass
class StrobeAttr:
    """Single-channel strobe attribute."""

    name: str = "strobe"

    @property
    def channel_count(self) -> int:
        return 1

    @property
    def default_value(self) -> float:
        return 0.0

    def encode(self, value: float) -> list[int]:
        return [_to_dmx(value)]


@dataclass
class PanAttr:
    """Pan position attribute (optional 16-bit)."""

    name: str = "pan"
    fine: bool = False

    @property
    def channel_count(self) -> int:
        return 2 if self.fine else 1

    @property
    def default_value(self) -> float:
        return 0.5  # Center position

    def encode(self, value: float) -> list[int]:
        if self.fine:
            coarse, fine = _to_dmx_16bit(value)
            return [coarse, fine]
        return [_to_dmx(value)]


@dataclass
class TiltAttr:
    """Tilt position attribute (optional 16-bit)."""

    name: str = "tilt"
    fine: bool = False

    @property
    def channel_count(self) -> int:
        return 2 if self.fine else 1

    @property
    def default_value(self) -> float:
        return 0.5  # Center position

    def encode(self, value: float) -> list[int]:
        if self.fine:
            coarse, fine = _to_dmx_16bit(value)
            return [coarse, fine]
        return [_to_dmx(value)]


@dataclass
class GoboAttr:
    """Gobo wheel selection attribute."""

    name: str = "gobo"

    @property
    def channel_count(self) -> int:
        return 1

    @property
    def default_value(self) -> float:
        return 0.0  # Open/no gobo

    def encode(self, value: float) -> list[int]:
        return [_to_dmx(value)]


@dataclass
class SkipAttr:
    """Placeholder for skipped/unused channels."""

    count: int = 1
    name: str = field(init=False, default="")

    def __post_init__(self) -> None:
        self.name = f"_skip_{id(self)}"

    @property
    def channel_count(self) -> int:
        return self.count

    @property
    def default_value(self) -> None:
        return None

    def encode(self, value: Any) -> list[int]:
        return [0] * self.count
