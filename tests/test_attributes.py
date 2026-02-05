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
from dmxld.color import Color


class TestDimmerAttr:
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


class TestColorAttributes:
    """All color attributes share unified 'color' name and encoding."""

    def test_rgb_encoding(self) -> None:
        attr = RGBAttr()
        assert attr.name == "color"
        assert attr.channel_count == 3
        assert attr.encode((1.0, 0.5, 0.0)) == [255, 127, 0]
        assert attr.encode(Color(1.0, 0.5, 0.0)) == [255, 127, 0]

    def test_rgbw_encoding(self) -> None:
        attr = RGBWAttr()
        assert attr.name == "color"
        assert attr.channel_count == 4
        assert attr.encode((1.0, 0.5, 0.0, 0.25)) == [255, 127, 0, 63]

    def test_rgba_encoding(self) -> None:
        attr = RGBAAttr()
        assert attr.name == "color"
        assert attr.channel_count == 4
        assert attr.encode((1.0, 0.5, 0.0, 0.25)) == [255, 127, 0, 63]

    def test_rgbaw_encoding(self) -> None:
        attr = RGBAWAttr()
        assert attr.name == "color"
        assert attr.channel_count == 5
        assert attr.encode((1.0, 0.5, 0.0, 0.25, 0.1)) == [255, 127, 0, 63, 25]


class TestColorConversion:
    """Color attributes convert between formats."""

    def test_rgb_from_rgbw(self) -> None:
        """RGBAttr converts RGBW input to RGB."""
        attr = RGBAttr()
        result = attr.convert((0.5, 0.0, 0.0, 0.5))
        assert result[0] == pytest.approx(1.0)  # r + w
        assert result[1] == pytest.approx(0.5)  # g + w
        assert result[2] == pytest.approx(0.5)  # b + w

    def test_rgbw_from_rgb_white(self) -> None:
        """RGBWAttr extracts white from RGB."""
        attr = RGBWAttr()
        result = attr.convert((1.0, 1.0, 1.0))
        assert result[:3] == pytest.approx((0.0, 0.0, 0.0))
        assert result[3] == pytest.approx(1.0)

    def test_rgbw_from_rgb_red(self) -> None:
        """Pure red stays red, no white extraction."""
        attr = RGBWAttr()
        result = attr.convert((1.0, 0.0, 0.0))
        assert result == pytest.approx((1.0, 0.0, 0.0, 0.0))

    def test_rgbw_preserves_rgbw(self) -> None:
        """RGBW input passes through unchanged."""
        attr = RGBWAttr()
        result = attr.convert((0.5, 0.5, 0.5, 0.5))
        assert result == (0.5, 0.5, 0.5, 0.5)

    def test_rgbw_strategy_override(self) -> None:
        """Per-attribute strategy overrides global."""
        attr = RGBWAttr(strategy="preserve_rgb")
        result = attr.convert((1.0, 0.5, 0.5))
        assert result[3] == pytest.approx(0.0)  # No white extraction

    def test_rgba_no_amber_for_pure_red(self) -> None:
        """Pure red should not extract amber."""
        attr = RGBAAttr()
        result = attr.convert((1.0, 0.0, 0.0))
        assert result[0] == pytest.approx(1.0)
        assert result[3] == pytest.approx(0.0)


class TestPanTiltAttr:
    def test_16bit_encoding(self) -> None:
        attr = PanAttr(fine=True)
        assert attr.channel_count == 2
        assert attr.default_value == 0.5


class TestSkipAttr:
    def test_unique_names(self) -> None:
        """Each SkipAttr gets a unique name."""
        attr1 = SkipAttr()
        attr2 = SkipAttr()
        assert attr1.name != attr2.name

    def test_multi_channel_skip(self) -> None:
        attr = SkipAttr(count=3)
        assert attr.channel_count == 3
        assert attr.encode(None) == [0, 0, 0]


class TestSegmentedAttributes:
    """Multi-segment color attributes."""

    @pytest.mark.parametrize("attr_cls,channels_per_seg", [
        (RGBAttr, 3),
        (RGBWAttr, 4),
        (RGBAAttr, 4),
        (RGBAWAttr, 5),
    ])
    def test_segment_channel_count(self, attr_cls, channels_per_seg) -> None:
        attr = attr_cls(segments=4)
        assert attr.channel_count == 4 * channels_per_seg

    def test_default_segments_is_one(self) -> None:
        assert RGBAttr().segments == 1
        assert RGBWAttr().segments == 1

    def test_encode_returns_single_segment(self) -> None:
        """encode() returns single segment (FixtureType handles multi-segment)."""
        attr = RGBWAttr(segments=4)
        result = attr.encode((1.0, 0.5, 0.0, 0.25))
        assert len(result) == 4
