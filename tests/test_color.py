"""Tests for Color class and conversion functions."""

import pytest

from dmxld.color import (
    Color,
    rgb,
    rgb_to_rgbw,
    rgbw_to_rgb,
    rgb_to_rgba,
    set_color_strategy,
    get_color_strategy,
)


class TestColor:
    """Unified Color type."""

    def test_tuple_subclass(self) -> None:
        c = Color(1.0, 0.5, 0.0)
        assert isinstance(c, tuple)
        assert len(c) == 3
        assert c[0] == 1.0

    def test_channel_properties(self) -> None:
        c = Color(1.0, 0.5, 0.25, 0.1)
        assert c.r == 1.0
        assert c.g == 0.5
        assert c.b == 0.25
        assert c.w == 0.1

    def test_missing_channels_default_zero(self) -> None:
        c = Color(1.0, 0.5)
        assert c.b == 0.0
        assert c.w == 0.0

    def test_rgb_helper(self) -> None:
        c = rgb(1.0, 0.5, 0.0)
        assert isinstance(c, Color)
        assert c.rgb == (1.0, 0.5, 0.0)

    def test_repr(self) -> None:
        assert repr(Color(1.0, 0.5, 0.0)) == "Color(1.0, 0.5, 0.0)"


class TestColorHSV:
    """HSV conversion via Color.from_hsv()."""

    def test_primary_colors(self) -> None:
        red = Color.from_hsv(0.0, 1.0, 1.0)
        assert red.rgb == pytest.approx((1.0, 0.0, 0.0))

        green = Color.from_hsv(1/3, 1.0, 1.0)
        assert green.rgb == pytest.approx((0.0, 1.0, 0.0))

        blue = Color.from_hsv(2/3, 1.0, 1.0)
        assert blue.rgb == pytest.approx((0.0, 0.0, 1.0))

    def test_desaturated(self) -> None:
        white = Color.from_hsv(0.0, 0.0, 1.0)
        assert white.rgb == pytest.approx((1.0, 1.0, 1.0))

        gray = Color.from_hsv(0.0, 0.0, 0.5)
        assert gray.rgb == pytest.approx((0.5, 0.5, 0.5))

    def test_hsv_property_roundtrip(self) -> None:
        c = Color(1.0, 0.0, 0.0)
        h, s, v = c.hsv
        assert h == pytest.approx(0.0)
        assert s == pytest.approx(1.0)
        assert v == pytest.approx(1.0)


class TestRGBToRGBW:
    """RGB to RGBW conversion."""

    def test_pure_white_extracts_white(self) -> None:
        r, g, b, w = rgb_to_rgbw(1.0, 1.0, 1.0)
        assert (r, g, b) == pytest.approx((0.0, 0.0, 0.0))
        assert w == pytest.approx(1.0)

    def test_pure_red_no_white(self) -> None:
        r, g, b, w = rgb_to_rgbw(1.0, 0.0, 0.0)
        assert (r, g, b, w) == pytest.approx((1.0, 0.0, 0.0, 0.0))

    def test_pink_extracts_partial_white(self) -> None:
        r, g, b, w = rgb_to_rgbw(1.0, 0.5, 0.5)
        assert w == pytest.approx(0.5)
        assert r == pytest.approx(0.5)

    def test_preserve_rgb_strategy(self) -> None:
        r, g, b, w = rgb_to_rgbw(1.0, 0.5, 0.5, strategy="preserve_rgb")
        assert w == pytest.approx(0.0)
        assert (r, g, b) == pytest.approx((1.0, 0.5, 0.5))


class TestRGBWToRGB:
    """RGBW to RGB conversion."""

    def test_white_adds_to_rgb(self) -> None:
        r, g, b = rgbw_to_rgb(0.0, 0.0, 0.0, 1.0)
        assert (r, g, b) == pytest.approx((1.0, 1.0, 1.0))

    def test_clamps_to_one(self) -> None:
        r, g, b = rgbw_to_rgb(1.0, 0.5, 0.5, 0.5)
        assert r == pytest.approx(1.0)  # clamped from 1.5


class TestRGBToRGBA:
    """RGB to RGBA (amber) conversion."""

    def test_pure_colors_no_amber(self) -> None:
        r, g, b, a = rgb_to_rgba(1.0, 0.0, 0.0)
        assert a == pytest.approx(0.0)

        r, g, b, a = rgb_to_rgba(0.0, 0.0, 1.0)
        assert a == pytest.approx(0.0)

    def test_warm_color_extracts_amber(self) -> None:
        r, g, b, a = rgb_to_rgba(1.0, 0.75, 0.0)
        assert a > 0.0


class TestColorStrategy:
    """Global color strategy."""

    def test_default_is_balanced(self) -> None:
        assert get_color_strategy() == "balanced"

    def test_set_strategy(self) -> None:
        original = get_color_strategy()
        try:
            set_color_strategy("preserve_rgb")
            assert get_color_strategy() == "preserve_rgb"
        finally:
            set_color_strategy(original)


class TestUnifiedColorKey:
    """Unified color key with automatic fixture-type conversion."""

    def test_rgb_fixture(self) -> None:
        from dmxld import FixtureType, DimmerAttr, RGBAttr, FixtureState

        ft = FixtureType(DimmerAttr(), RGBAttr())
        state = FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))
        encoded = ft.encode(state)
        assert encoded == {0: 255, 1: 255, 2: 0, 3: 0}

    def test_rgbw_fixture_converts_white(self) -> None:
        from dmxld import FixtureType, DimmerAttr, RGBWAttr, FixtureState

        ft = FixtureType(DimmerAttr(), RGBWAttr())
        state = FixtureState(dimmer=1.0, color=(1.0, 1.0, 1.0))
        encoded = ft.encode(state)
        assert (encoded[1], encoded[2], encoded[3], encoded[4]) == (0, 0, 0, 255)

    def test_raw_bypasses_conversion(self) -> None:
        from dmxld import FixtureType, DimmerAttr, RGBWAttr, FixtureState, Raw

        ft = FixtureType(DimmerAttr(), RGBWAttr())
        state = FixtureState(dimmer=1.0, color=Raw(0.5, 0.5, 0.5, 0.5))
        encoded = ft.encode(state)
        assert (encoded[1], encoded[2], encoded[3], encoded[4]) == (127, 127, 127, 127)

    def test_color_from_hsv(self) -> None:
        from dmxld import FixtureType, DimmerAttr, RGBAttr, FixtureState, Color

        ft = FixtureType(DimmerAttr(), RGBAttr())
        state = FixtureState(dimmer=1.0, color=Color.from_hsv(0.0, 1.0, 1.0))
        encoded = ft.encode(state)
        assert (encoded[1], encoded[2], encoded[3]) == (255, 0, 0)
