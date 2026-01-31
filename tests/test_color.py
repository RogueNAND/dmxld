"""Tests for Color class."""

from dmxld.color import Color, rgb, rgbw


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

    def test_rgbw_helper(self) -> None:
        c = rgbw(1.0, 0.5, 0.0, 0.25)
        assert isinstance(c, Color)
        assert len(c) == 4
        assert c.r == 1.0
        assert c.g == 0.5
        assert c.b == 0.0
        assert c.w == 0.25

    def test_color_repr(self) -> None:
        c = Color(1.0, 0.5, 0.0)
        assert repr(c) == "Color(1.0, 0.5, 0.0)"

    def test_color_usable_in_fixture_state(self) -> None:
        from dmxld import FixtureState

        state = FixtureState(rgb=Color(1.0, 0.0, 0.0))
        assert state["rgb"] == (1.0, 0.0, 0.0)

    def test_plain_tuple_still_works(self) -> None:
        from dmxld import FixtureState, FixtureType, DimmerAttr, RGBAttr

        ft = FixtureType(DimmerAttr(), RGBAttr())
        state = FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0))
        encoded = ft.encode(state)
        assert encoded == {0: 255, 1: 255, 2: 0, 3: 0}
