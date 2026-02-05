"""Tests for attribute encoding."""

import pytest

from dmxld.attributes import (
    DimmerAttr,
    RGBAttr,
    RGBWAttr,
    RGBAAttr,
    RGBAWAttr,
    PanAttr,
    SkipAttr,
)
from dmxld.color import Color, rgb


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

    def test_unified_name(self) -> None:
        attr = RGBAttr()
        assert attr.name == "color"
        assert attr.raw_name == "raw_rgb"

    def test_convert_from_rgb(self) -> None:
        attr = RGBAttr()
        result = attr.convert((1.0, 0.5, 0.0))
        assert result == (1.0, 0.5, 0.0)

    def test_convert_from_rgbw(self) -> None:
        attr = RGBAttr()
        # RGBW with white=0.5 should add white to RGB
        result = attr.convert((0.5, 0.0, 0.0, 0.5))
        assert result[0] == pytest.approx(1.0)  # r + w
        assert result[1] == pytest.approx(0.5)  # g + w
        assert result[2] == pytest.approx(0.5)  # b + w


class TestRGBWAttr:
    """RGBW color encoding."""

    def test_encoding(self) -> None:
        attr = RGBWAttr()
        assert attr.channel_count == 4
        assert attr.encode((1.0, 0.5, 0.0, 0.25)) == [255, 127, 0, 63]

    def test_color_object(self) -> None:
        attr = RGBWAttr()
        assert attr.encode(Color(1.0, 0.0, 0.0, 0.5)) == [255, 0, 0, 127]

    def test_unified_name(self) -> None:
        attr = RGBWAttr()
        assert attr.name == "color"
        assert attr.raw_name == "raw_rgbw"

    def test_convert_from_rgb(self) -> None:
        attr = RGBWAttr()
        # Pure white RGB should become pure white RGBW
        result = attr.convert((1.0, 1.0, 1.0))
        assert result[0] == pytest.approx(0.0)  # red extracted
        assert result[1] == pytest.approx(0.0)  # green extracted
        assert result[2] == pytest.approx(0.0)  # blue extracted
        assert result[3] == pytest.approx(1.0)  # white

    def test_convert_from_rgb_pure_red(self) -> None:
        attr = RGBWAttr()
        result = attr.convert((1.0, 0.0, 0.0))
        assert result[0] == pytest.approx(1.0)  # red stays
        assert result[1] == pytest.approx(0.0)
        assert result[2] == pytest.approx(0.0)
        assert result[3] == pytest.approx(0.0)  # no white

    def test_convert_preserves_rgbw(self) -> None:
        attr = RGBWAttr()
        # If input is already RGBW, keep as-is
        result = attr.convert((0.5, 0.5, 0.5, 0.5))
        assert result == (0.5, 0.5, 0.5, 0.5)

    def test_strategy_override(self) -> None:
        attr = RGBWAttr(strategy="preserve_rgb")
        result = attr.convert((1.0, 0.5, 0.5))
        assert result[0] == pytest.approx(1.0)
        assert result[1] == pytest.approx(0.5)
        assert result[2] == pytest.approx(0.5)
        assert result[3] == pytest.approx(0.0)  # No white extraction


class TestRGBAAttr:
    """RGBA (amber) color encoding."""

    def test_encoding(self) -> None:
        attr = RGBAAttr()
        assert attr.channel_count == 4
        assert attr.encode((1.0, 0.5, 0.0, 0.25)) == [255, 127, 0, 63]

    def test_unified_name(self) -> None:
        attr = RGBAAttr()
        assert attr.name == "color"
        assert attr.raw_name == "raw_rgba"

    def test_convert_from_rgb(self) -> None:
        attr = RGBAAttr()
        # Pure red should stay red, no amber
        result = attr.convert((1.0, 0.0, 0.0))
        assert result[0] == pytest.approx(1.0)
        assert result[3] == pytest.approx(0.0)  # No amber


class TestRGBAWAttr:
    """RGBAW (amber + white) color encoding."""

    def test_encoding(self) -> None:
        attr = RGBAWAttr()
        assert attr.channel_count == 5
        assert attr.encode((1.0, 0.5, 0.0, 0.25, 0.1)) == [255, 127, 0, 63, 25]

    def test_unified_name(self) -> None:
        attr = RGBAWAttr()
        assert attr.name == "color"
        assert attr.raw_name == "raw_rgbaw"


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


class TestSegmentedAttributes:
    """Multi-segment attribute support."""

    def test_rgb_segments_channel_count(self) -> None:
        """RGBAttr segments multiplies channel count."""
        attr = RGBAttr(segments=4)
        assert attr.channel_count == 12  # 4 * 3

    def test_rgbw_segments_channel_count(self) -> None:
        """RGBWAttr segments multiplies channel count."""
        attr = RGBWAttr(segments=4)
        assert attr.channel_count == 16  # 4 * 4

    def test_rgba_segments_channel_count(self) -> None:
        """RGBAAttr segments multiplies channel count."""
        attr = RGBAAttr(segments=2)
        assert attr.channel_count == 8  # 2 * 4

    def test_rgbaw_segments_channel_count(self) -> None:
        """RGBAWAttr segments multiplies channel count."""
        attr = RGBAWAttr(segments=3)
        assert attr.channel_count == 15  # 3 * 5

    def test_default_segments_is_one(self) -> None:
        """Default segments is 1 (non-segmented)."""
        assert RGBAttr().segments == 1
        assert RGBWAttr().segments == 1
        assert RGBAAttr().segments == 1
        assert RGBAWAttr().segments == 1

    def test_encode_still_returns_single_segment(self) -> None:
        """encode() still returns single segment (encoding done at FixtureType level)."""
        attr = RGBWAttr(segments=4)
        # encode() only encodes one segment's worth of data
        result = attr.encode((1.0, 0.5, 0.0, 0.25))
        assert len(result) == 4  # Still 4 bytes for a single color
