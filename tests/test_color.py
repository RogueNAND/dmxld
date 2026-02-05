"""Tests for Color class and conversion functions."""

import pytest

from dmxld.color import (
    Color,
    rgb,
    hsv_to_rgb,
    rgb_to_hsv,
    rgb_to_rgbw,
    rgbw_to_rgb,
    rgb_to_rgba,
    rgba_to_rgb,
    set_color_strategy,
    get_color_strategy,
)


class TestColor:
    """Unified Color type tests."""

    def test_color_is_tuple(self) -> None:
        c = Color(1.0, 0.5, 0.0)
        assert isinstance(c, tuple)
        assert len(c) == 3
        assert c[0] == 1.0
        assert c[1] == 0.5
        assert c[2] == 0.0

    def test_color_properties(self) -> None:
        c = Color(1.0, 0.5, 0.25, 0.1)
        assert c.r == 1.0
        assert c.g == 0.5
        assert c.b == 0.25
        assert c.w == 0.1

    def test_color_missing_channels(self) -> None:
        c = Color(1.0, 0.5)
        assert c.r == 1.0
        assert c.g == 0.5
        assert c.b == 0.0  # Missing, defaults to 0
        assert c.w == 0.0  # Missing, defaults to 0

    def test_rgb_helper(self) -> None:
        c = rgb(1.0, 0.5, 0.0)
        assert isinstance(c, Color)
        assert len(c) == 3
        assert c.r == 1.0
        assert c.g == 0.5
        assert c.b == 0.0

    def test_color_repr(self) -> None:
        c = Color(1.0, 0.5, 0.0)
        assert repr(c) == "Color(1.0, 0.5, 0.0)"

    def test_color_usable_in_fixture_state(self) -> None:
        from dmxld import FixtureState

        state = FixtureState(color=Color(1.0, 0.0, 0.0))
        assert state["color"] == (1.0, 0.0, 0.0)

    def test_plain_tuple_still_works(self) -> None:
        from dmxld import FixtureState, FixtureType, DimmerAttr, RGBAttr

        ft = FixtureType(DimmerAttr(), RGBAttr())
        state = FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))
        encoded = ft.encode(state)
        assert encoded == {0: 255, 1: 255, 2: 0, 3: 0}


class TestColorFromHSV:
    """Color.from_hsv() tests."""

    def test_from_hsv_red(self) -> None:
        c = Color.from_hsv(0.0, 1.0, 1.0)
        assert c.r == pytest.approx(1.0)
        assert c.g == pytest.approx(0.0)
        assert c.b == pytest.approx(0.0)

    def test_from_hsv_green(self) -> None:
        c = Color.from_hsv(1 / 3, 1.0, 1.0)
        assert c.r == pytest.approx(0.0)
        assert c.g == pytest.approx(1.0)
        assert c.b == pytest.approx(0.0)

    def test_from_hsv_blue(self) -> None:
        c = Color.from_hsv(2 / 3, 1.0, 1.0)
        assert c.r == pytest.approx(0.0)
        assert c.g == pytest.approx(0.0)
        assert c.b == pytest.approx(1.0)

    def test_from_hsv_white(self) -> None:
        c = Color.from_hsv(0.0, 0.0, 1.0)
        assert c.r == pytest.approx(1.0)
        assert c.g == pytest.approx(1.0)
        assert c.b == pytest.approx(1.0)

    def test_from_hsv_gray(self) -> None:
        c = Color.from_hsv(0.0, 0.0, 0.5)
        assert c.r == pytest.approx(0.5)
        assert c.g == pytest.approx(0.5)
        assert c.b == pytest.approx(0.5)


class TestColorRGBHSVProperties:
    """Color .rgb and .hsv property tests."""

    def test_rgb_property(self) -> None:
        c = Color(1.0, 0.5, 0.25)
        assert c.rgb == (1.0, 0.5, 0.25)

    def test_hsv_property_red(self) -> None:
        c = Color(1.0, 0.0, 0.0)
        h, s, v = c.hsv
        assert h == pytest.approx(0.0)
        assert s == pytest.approx(1.0)
        assert v == pytest.approx(1.0)

    def test_hsv_property_white(self) -> None:
        c = Color(1.0, 1.0, 1.0)
        h, s, v = c.hsv
        assert s == pytest.approx(0.0)
        assert v == pytest.approx(1.0)


class TestHSVToRGB:
    """hsv_to_rgb() function tests."""

    def test_primary_red(self) -> None:
        r, g, b = hsv_to_rgb(0.0, 1.0, 1.0)
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)

    def test_primary_green(self) -> None:
        r, g, b = hsv_to_rgb(1 / 3, 1.0, 1.0)
        assert r == pytest.approx(0.0)
        assert g == pytest.approx(1.0)
        assert b == pytest.approx(0.0)

    def test_primary_blue(self) -> None:
        r, g, b = hsv_to_rgb(2 / 3, 1.0, 1.0)
        assert r == pytest.approx(0.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(1.0)

    def test_yellow(self) -> None:
        r, g, b = hsv_to_rgb(1 / 6, 1.0, 1.0)
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(1.0)
        assert b == pytest.approx(0.0)

    def test_cyan(self) -> None:
        r, g, b = hsv_to_rgb(0.5, 1.0, 1.0)
        assert r == pytest.approx(0.0)
        assert g == pytest.approx(1.0)
        assert b == pytest.approx(1.0)

    def test_no_saturation(self) -> None:
        r, g, b = hsv_to_rgb(0.5, 0.0, 0.75)
        assert r == pytest.approx(0.75)
        assert g == pytest.approx(0.75)
        assert b == pytest.approx(0.75)


class TestRGBToHSV:
    """rgb_to_hsv() function tests."""

    def test_red(self) -> None:
        h, s, v = rgb_to_hsv(1.0, 0.0, 0.0)
        assert h == pytest.approx(0.0)
        assert s == pytest.approx(1.0)
        assert v == pytest.approx(1.0)

    def test_green(self) -> None:
        h, s, v = rgb_to_hsv(0.0, 1.0, 0.0)
        assert h == pytest.approx(1 / 3)
        assert s == pytest.approx(1.0)
        assert v == pytest.approx(1.0)

    def test_blue(self) -> None:
        h, s, v = rgb_to_hsv(0.0, 0.0, 1.0)
        assert h == pytest.approx(2 / 3)
        assert s == pytest.approx(1.0)
        assert v == pytest.approx(1.0)

    def test_white(self) -> None:
        h, s, v = rgb_to_hsv(1.0, 1.0, 1.0)
        assert s == pytest.approx(0.0)
        assert v == pytest.approx(1.0)

    def test_gray(self) -> None:
        h, s, v = rgb_to_hsv(0.5, 0.5, 0.5)
        assert s == pytest.approx(0.0)
        assert v == pytest.approx(0.5)


class TestRGBToRGBW:
    """rgb_to_rgbw() conversion tests."""

    def test_pure_white(self) -> None:
        r, g, b, w = rgb_to_rgbw(1.0, 1.0, 1.0)
        assert r == pytest.approx(0.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)
        assert w == pytest.approx(1.0)

    def test_pure_red(self) -> None:
        r, g, b, w = rgb_to_rgbw(1.0, 0.0, 0.0)
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)
        assert w == pytest.approx(0.0)

    def test_pink(self) -> None:
        # Pink = red + white
        r, g, b, w = rgb_to_rgbw(1.0, 0.5, 0.5)
        assert r == pytest.approx(0.5)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)
        assert w == pytest.approx(0.5)

    def test_preserve_rgb_strategy(self) -> None:
        r, g, b, w = rgb_to_rgbw(1.0, 0.5, 0.5, strategy="preserve_rgb")
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(0.5)
        assert b == pytest.approx(0.5)
        assert w == pytest.approx(0.0)


class TestRGBWToRGB:
    """rgbw_to_rgb() conversion tests."""

    def test_white_only(self) -> None:
        r, g, b = rgbw_to_rgb(0.0, 0.0, 0.0, 1.0)
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(1.0)
        assert b == pytest.approx(1.0)

    def test_red_and_white(self) -> None:
        r, g, b = rgbw_to_rgb(0.5, 0.0, 0.0, 0.5)
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(0.5)
        assert b == pytest.approx(0.5)

    def test_clamps_to_one(self) -> None:
        r, g, b = rgbw_to_rgb(1.0, 0.5, 0.5, 0.5)
        assert r == pytest.approx(1.0)  # Clamped from 1.5
        assert g == pytest.approx(1.0)  # Clamped from 1.0
        assert b == pytest.approx(1.0)  # Clamped from 1.0


class TestRGBToRGBA:
    """rgb_to_rgba() conversion tests."""

    def test_pure_red(self) -> None:
        r, g, b, a = rgb_to_rgba(1.0, 0.0, 0.0)
        assert r == pytest.approx(1.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(0.0)
        assert a == pytest.approx(0.0)

    def test_pure_blue(self) -> None:
        # Blue shouldn't extract amber
        r, g, b, a = rgb_to_rgba(0.0, 0.0, 1.0)
        assert r == pytest.approx(0.0)
        assert g == pytest.approx(0.0)
        assert b == pytest.approx(1.0)
        assert a == pytest.approx(0.0)

    def test_warm_color(self) -> None:
        # Warm orange should extract some amber
        r, g, b, a = rgb_to_rgba(1.0, 0.75, 0.0)
        assert a > 0.0  # Some amber extracted
        assert b == pytest.approx(0.0)


class TestColorStrategy:
    """Global color strategy tests."""

    def test_default_strategy(self) -> None:
        assert get_color_strategy() == "balanced"

    def test_set_strategy(self) -> None:
        original = get_color_strategy()
        try:
            set_color_strategy("preserve_rgb")
            assert get_color_strategy() == "preserve_rgb"
        finally:
            set_color_strategy(original)


class TestUnifiedColorKey:
    """Test unified color key with automatic conversion."""

    def test_rgb_fixture_with_color_tuple(self) -> None:
        from dmxld import FixtureType, DimmerAttr, RGBAttr, FixtureState

        ft = FixtureType(DimmerAttr(), RGBAttr())
        state = FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))
        encoded = ft.encode(state)
        # Dimmer at 0, RGB at 1-3
        assert encoded[0] == 255  # dimmer
        assert encoded[1] == 255  # red
        assert encoded[2] == 0    # green
        assert encoded[3] == 0    # blue

    def test_rgbw_fixture_with_color_tuple(self) -> None:
        from dmxld import FixtureType, DimmerAttr, RGBWAttr, FixtureState

        ft = FixtureType(DimmerAttr(), RGBWAttr())
        # Pure white should convert to use white LED
        state = FixtureState(dimmer=1.0, color=(1.0, 1.0, 1.0))
        encoded = ft.encode(state)
        assert encoded[0] == 255  # dimmer
        assert encoded[1] == 0    # red (extracted as white)
        assert encoded[2] == 0    # green
        assert encoded[3] == 0    # blue
        assert encoded[4] == 255  # white

    def test_rgbw_fixture_with_pure_red(self) -> None:
        from dmxld import FixtureType, DimmerAttr, RGBWAttr, FixtureState

        ft = FixtureType(DimmerAttr(), RGBWAttr())
        state = FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))
        encoded = ft.encode(state)
        assert encoded[0] == 255  # dimmer
        assert encoded[1] == 255  # red
        assert encoded[2] == 0    # green
        assert encoded[3] == 0    # blue
        assert encoded[4] == 0    # white (no white component)

    def test_raw_bypasses_conversion(self) -> None:
        from dmxld import FixtureType, DimmerAttr, RGBWAttr, FixtureState, Raw

        ft = FixtureType(DimmerAttr(), RGBWAttr())
        state = FixtureState(dimmer=1.0, color=Raw(0.5, 0.5, 0.5, 0.5))
        encoded = ft.encode(state)
        assert encoded[0] == 255  # dimmer
        assert encoded[1] == 127  # red
        assert encoded[2] == 127  # green
        assert encoded[3] == 127  # blue
        assert encoded[4] == 127  # white

    def test_color_object_with_hsv(self) -> None:
        from dmxld import FixtureType, DimmerAttr, RGBAttr, FixtureState, Color

        ft = FixtureType(DimmerAttr(), RGBAttr())
        # Red from HSV
        state = FixtureState(dimmer=1.0, color=Color.from_hsv(0.0, 1.0, 1.0))
        encoded = ft.encode(state)
        assert encoded[0] == 255  # dimmer
        assert encoded[1] == 255  # red
        assert encoded[2] == 0    # green
        assert encoded[3] == 0    # blue
