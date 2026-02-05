"""Unified Color type with HSV support and automatic conversion."""

from __future__ import annotations

from typing import Literal

# Color conversion strategies
ColorStrategy = Literal["balanced", "preserve_rgb", "max_white"]

# Global color configuration
_color_config: dict[str, ColorStrategy] = {"strategy": "balanced"}


def set_color_strategy(strategy: ColorStrategy) -> None:
    """Set the global color conversion strategy.

    Args:
        strategy: One of:
            - "balanced": Extract white from common RGB (default)
            - "preserve_rgb": Keep RGB as-is, white=0
            - "max_white": Maximize white LED usage
    """
    _color_config["strategy"] = strategy


def get_color_strategy() -> ColorStrategy:
    """Get the current global color conversion strategy."""
    return _color_config["strategy"]


# -----------------------------------------------------------------------------
# HSV <-> RGB Conversion
# -----------------------------------------------------------------------------


def hsv_to_rgb(h: float, s: float, v: float) -> tuple[float, float, float]:
    """Convert HSV to RGB (all values 0.0-1.0).

    Args:
        h: Hue (0.0-1.0, wraps around)
        s: Saturation (0.0-1.0)
        v: Value/brightness (0.0-1.0)

    Returns:
        Tuple of (red, green, blue), each 0.0-1.0
    """
    if s == 0.0:
        return (v, v, v)
    i = int(h * 6.0)
    f = (h * 6.0) - i
    p = v * (1.0 - s)
    q = v * (1.0 - s * f)
    t = v * (1.0 - s * (1.0 - f))
    i = i % 6
    if i == 0:
        return (v, t, p)
    if i == 1:
        return (q, v, p)
    if i == 2:
        return (p, v, t)
    if i == 3:
        return (p, q, v)
    if i == 4:
        return (t, p, v)
    return (v, p, q)


def rgb_to_hsv(r: float, g: float, b: float) -> tuple[float, float, float]:
    """Convert RGB to HSV (all values 0.0-1.0).

    Args:
        r: Red (0.0-1.0)
        g: Green (0.0-1.0)
        b: Blue (0.0-1.0)

    Returns:
        Tuple of (hue, saturation, value), each 0.0-1.0
    """
    max_c = max(r, g, b)
    min_c = min(r, g, b)
    v = max_c

    if max_c == min_c:
        return (0.0, 0.0, v)

    diff = max_c - min_c
    s = diff / max_c

    if max_c == r:
        h = (g - b) / diff
        if g < b:
            h += 6.0
    elif max_c == g:
        h = (b - r) / diff + 2.0
    else:
        h = (r - g) / diff + 4.0

    h /= 6.0
    return (h, s, v)


# -----------------------------------------------------------------------------
# RGB <-> RGBW Conversion
# -----------------------------------------------------------------------------


def rgb_to_rgbw(
    r: float, g: float, b: float, strategy: ColorStrategy | None = None
) -> tuple[float, float, float, float]:
    """Convert RGB to RGBW.

    Args:
        r: Red (0.0-1.0)
        g: Green (0.0-1.0)
        b: Blue (0.0-1.0)
        strategy: Conversion strategy (uses global if None)

    Returns:
        Tuple of (red, green, blue, white), each 0.0-1.0

    Examples:
        (1, 1, 1) -> (0, 0, 0, 1)      Pure white uses white LED only
        (1, 0, 0) -> (1, 0, 0, 0)      Pure red stays red
        (1, 0.5, 0.5) -> (0.5, 0, 0, 0.5)  Pink = red + white
    """
    if strategy is None:
        strategy = get_color_strategy()

    if strategy == "preserve_rgb":
        return (r, g, b, 0.0)

    if strategy == "max_white":
        # Maximize white LED usage
        w = min(r, g, b)
        if w > 0:
            # Scale remaining RGB to compensate
            remaining = 1.0 - w
            if remaining > 0:
                r_out = (r - w) / (1.0 - w) * remaining if r > w else 0.0
                g_out = (g - w) / (1.0 - w) * remaining if g > w else 0.0
                b_out = (b - w) / (1.0 - w) * remaining if b > w else 0.0
                return (r_out, g_out, b_out, w)
        return (r, g, b, 0.0)

    # Default "balanced" strategy: extract common white component
    w = min(r, g, b)
    return (r - w, g - w, b - w, w)


def rgbw_to_rgb(
    r: float, g: float, b: float, w: float
) -> tuple[float, float, float]:
    """Convert RGBW to RGB.

    Args:
        r: Red (0.0-1.0)
        g: Green (0.0-1.0)
        b: Blue (0.0-1.0)
        w: White (0.0-1.0)

    Returns:
        Tuple of (red, green, blue), each 0.0-1.0, clamped to 1.0
    """
    return (min(1.0, r + w), min(1.0, g + w), min(1.0, b + w))


# -----------------------------------------------------------------------------
# RGB <-> RGBA (Amber) Conversion
# -----------------------------------------------------------------------------


def rgb_to_rgba(r: float, g: float, b: float) -> tuple[float, float, float, float]:
    """Convert RGB to RGBA (with amber extraction).

    Amber is approximately (1.0, 0.75, 0.0) - a warm orange color.

    Args:
        r: Red (0.0-1.0)
        g: Green (0.0-1.0)
        b: Blue (0.0-1.0)

    Returns:
        Tuple of (red, green, blue, amber), each 0.0-1.0
    """
    # Amber shouldn't be present in blue-ish colors
    if b > 0.5:
        return (r, g, b, 0.0)

    # Extract amber from the "warm" component
    # Amber ≈ (1.0, 0.75, 0.0)
    if g > 0:
        amber = min(r, g / 0.75)
    else:
        amber = 0.0

    amber = min(amber, 1.0 - b)
    amber = max(0.0, amber)

    r_out = max(0.0, r - amber)
    g_out = max(0.0, g - amber * 0.75)

    return (r_out, g_out, b, amber)


def rgba_to_rgb(
    r: float, g: float, b: float, a: float
) -> tuple[float, float, float]:
    """Convert RGBA to RGB.

    Args:
        r: Red (0.0-1.0)
        g: Green (0.0-1.0)
        b: Blue (0.0-1.0)
        a: Amber (0.0-1.0)

    Returns:
        Tuple of (red, green, blue), each 0.0-1.0, clamped to 1.0
    """
    # Amber ≈ (1.0, 0.75, 0.0)
    return (min(1.0, r + a), min(1.0, g + a * 0.75), b)


# -----------------------------------------------------------------------------
# Color Class
# -----------------------------------------------------------------------------


class Color(tuple[float, ...]):
    """Color with HSV support and automatic conversion.

    Stores color internally as RGB. Supports HSV input via from_hsv().

    Examples:
        Color(1.0, 0.0, 0.0)           # RGB red
        Color.from_hsv(0.0, 1.0, 1.0)  # HSV red
        color.rgb                       # Get RGB tuple
        color.hsv                       # Get HSV tuple
    """

    def __new__(cls, *values: float) -> Color:
        return super().__new__(cls, values)

    @classmethod
    def from_hsv(cls, h: float, s: float, v: float) -> Color:
        """Create a Color from HSV values.

        Args:
            h: Hue (0.0-1.0, wraps around)
            s: Saturation (0.0-1.0)
            v: Value/brightness (0.0-1.0)
        """
        r, g, b = hsv_to_rgb(h, s, v)
        return cls(r, g, b)

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
        """White channel (for RGBW colors)."""
        return self[3] if len(self) > 3 else 0.0

    @property
    def rgb(self) -> tuple[float, float, float]:
        """Get RGB representation."""
        return (self.r, self.g, self.b)

    @property
    def hsv(self) -> tuple[float, float, float]:
        """Get HSV representation."""
        return rgb_to_hsv(self.r, self.g, self.b)

    def __repr__(self) -> str:
        values = ", ".join(f"{v}" for v in self)
        return f"Color({values})"


# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------


def rgb(r: float, g: float, b: float) -> Color:
    """Create an RGB color."""
    return Color(r, g, b)


# -----------------------------------------------------------------------------
# Raw Color Marker
# -----------------------------------------------------------------------------


class Raw(tuple[float, ...]):
    """Marker for raw color values that bypass conversion.

    Use this when you want to send exact channel values to a fixture
    without any automatic RGB→RGBW or similar conversion.

    Examples:
        # Direct RGBW values (no conversion)
        FixtureState(color=Raw(1.0, 0.0, 0.0, 0.5))

        # Per-segment raw values
        FixtureState(color_0=Raw(0.5, 0.0, 0.0, 0.0), color_1=(1.0, 0.0, 0.0))

        # Compare to normal usage (conversion applied):
        FixtureState(color=(1.0, 0.0, 0.0))  # RGB → converted to fixture's format
    """

    def __new__(cls, *values: float) -> Raw:
        return super().__new__(cls, values)

    def __repr__(self) -> str:
        values = ", ".join(f"{v}" for v in self)
        return f"Raw({values})"
