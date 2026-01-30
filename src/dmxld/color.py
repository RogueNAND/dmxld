"""Color types with format conversion."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RGB:
    """RGB color (normalized 0.0-1.0)."""

    r: float
    g: float
    b: float

    def as_tuple(self) -> tuple[float, float, float]:
        return (self.r, self.g, self.b)


@dataclass(frozen=True)
class RGBW:
    """RGBW color (normalized 0.0-1.0)."""

    r: float
    g: float
    b: float
    w: float

    def as_tuple(self) -> tuple[float, float, float, float]:
        return (self.r, self.g, self.b, self.w)
