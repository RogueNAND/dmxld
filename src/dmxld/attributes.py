"""Composable fixture attributes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from dmxld.color import RGB, RGBW


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
    """3-channel RGB color attribute."""

    name: str = "rgb"

    @property
    def channel_count(self) -> int:
        return 3

    @property
    def default_value(self) -> tuple[float, float, float]:
        return (0.0, 0.0, 0.0)

    def encode(self, value: tuple[float, float, float] | RGB) -> list[int]:
        if isinstance(value, RGB):
            value = value.as_tuple()
        return [_to_dmx(value[0]), _to_dmx(value[1]), _to_dmx(value[2])]


@dataclass
class RGBWAttr:
    """4-channel RGBW color attribute."""

    name: str = "rgbw"

    @property
    def channel_count(self) -> int:
        return 4

    @property
    def default_value(self) -> tuple[float, float, float, float]:
        return (0.0, 0.0, 0.0, 0.0)

    def encode(self, value: tuple[float, float, float, float] | RGBW) -> list[int]:
        if isinstance(value, RGBW):
            value = value.as_tuple()
        return [_to_dmx(v) for v in value[:4]]


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
