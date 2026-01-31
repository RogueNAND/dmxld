"""Tests for attribute encoding."""

import pytest

from dmxld.attributes import (
    DimmerAttr,
    RGBAttr,
    RGBWAttr,
    PanAttr,
    SkipAttr,
)
from dmxld.color import Color, rgb, rgbw


class TestDimmerAttr:
    """8-bit and 16-bit dimmer encoding."""

    def test_8bit_encoding(self) -> None:
        attr = DimmerAttr()
        assert attr.channel_count == 1
        assert attr.encode(0.0) == [0]
        assert attr.encode(0.5) == [127]
        assert attr.encode(1.0) == [255]

    def test_16bit_encoding(self) -> None:
        attr = DimmerAttr(fine=True)
        assert attr.channel_count == 2
        assert attr.encode(0.0) == [0, 0]
        assert attr.encode(1.0) == [255, 255]


class TestRGBAttr:
    """RGB color encoding."""

    def test_encoding(self) -> None:
        attr = RGBAttr()
        assert attr.channel_count == 3
        assert attr.encode((1.0, 0.5, 0.0)) == [255, 127, 0]

    def test_color_object(self) -> None:
        attr = RGBAttr()
        assert attr.encode(Color(1.0, 0.5, 0.0)) == [255, 127, 0]

    def test_rgb_helper(self) -> None:
        attr = RGBAttr()
        assert attr.encode(rgb(1.0, 0.5, 0.0)) == [255, 127, 0]


class TestRGBWAttr:
    """RGBW color encoding."""

    def test_encoding(self) -> None:
        attr = RGBWAttr()
        assert attr.channel_count == 4
        assert attr.encode((1.0, 0.5, 0.0, 0.25)) == [255, 127, 0, 63]

    def test_color_object(self) -> None:
        attr = RGBWAttr()
        assert attr.encode(Color(1.0, 0.0, 0.0, 0.5)) == [255, 0, 0, 127]

    def test_rgbw_helper(self) -> None:
        attr = RGBWAttr()
        assert attr.encode(rgbw(1.0, 0.0, 0.0, 0.5)) == [255, 0, 0, 127]


class TestPanTiltAttr:
    """16-bit pan/tilt encoding."""

    def test_16bit_encoding(self) -> None:
        attr = PanAttr(fine=True)
        assert attr.channel_count == 2
        assert attr.default_value == 0.5  # Center position


class TestSkipAttr:
    """Skip channels for unused DMX slots."""

    def test_unique_names(self) -> None:
        """Each SkipAttr gets a unique name to avoid conflicts."""
        attr1 = SkipAttr()
        attr2 = SkipAttr()
        assert attr1.name != attr2.name

    def test_multi_channel_skip(self) -> None:
        attr = SkipAttr(count=3)
        assert attr.channel_count == 3
        assert attr.encode(None) == [0, 0, 0]
