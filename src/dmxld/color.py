"""Unified Color type for any channel count."""

from __future__ import annotations


class Color(tuple[float, ...]):
    """Color with any number of channels (normalized 0.0-1.0).

    Works directly as a tuple in FixtureState.

    Examples:
        Color(1.0, 0.0, 0.0)           # RGB red
        Color(1.0, 0.0, 0.0, 0.5)      # RGBW red + 50% white
        rgb(1.0, 0.5, 0.0)             # Shorthand for RGB
        rgbw(1.0, 0.5, 0.0, 0.25)      # Shorthand for RGBW
    """

    def __new__(cls, *values: float) -> Color:
        return super().__new__(cls, values)

    @property
    def r(self) -> float:
        """Red channel."""
        return self[0] if len(self) > 0 else 0.0

    @property
    def g(self) -> float:
        """Green channel."""
        return self[1] if len(self) > 1 else 0.0

    @property
    def b(self) -> float:
        """Blue channel."""
        return self[2] if len(self) > 2 else 0.0

    @property
    def w(self) -> float:
        """White channel."""
        return self[3] if len(self) > 3 else 0.0

    def __repr__(self) -> str:
        values = ", ".join(f"{v}" for v in self)
        return f"Color({values})"


def rgb(r: float, g: float, b: float) -> Color:
    """Create an RGB color."""
    return Color(r, g, b)


def rgbw(r: float, g: float, b: float, w: float) -> Color:
    """Create an RGBW color."""
    return Color(r, g, b, w)
