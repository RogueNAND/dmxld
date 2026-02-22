"""Tests for blend operations and delta compositing."""

import pytest

from dmxld.blend import BlendOp, FixtureDelta, apply_delta, merge_deltas
from dmxld.color import Color
from dmxld.model import FixtureState


class TestBlendOps:
    def test_set_overwrites(self) -> None:
        state = FixtureState(dimmer=0.5)
        delta = FixtureDelta(dimmer=(BlendOp.SET, 0.8))
        assert apply_delta(state, delta)["dimmer"] == 0.8

    def test_mul_multiplies(self) -> None:
        state = FixtureState(dimmer=0.8)
        delta = FixtureDelta(dimmer=(BlendOp.MUL, 0.5))
        assert apply_delta(state, delta)["dimmer"] == pytest.approx(0.4)

    def test_add_clamp(self) -> None:
        state = FixtureState(dimmer=0.3)
        delta = FixtureDelta(dimmer=(BlendOp.ADD_CLAMP, 0.4))
        assert apply_delta(state, delta)["dimmer"] == pytest.approx(0.7)

    def test_tuple_blending(self) -> None:
        state = FixtureState(rgb=(1.0, 0.8, 0.6))
        delta = FixtureDelta(rgb=(BlendOp.MUL, (0.5, 0.5, 0.5)))
        result = apply_delta(state, delta)["rgb"]
        assert result == pytest.approx((0.5, 0.4, 0.3))


class TestClamping:
    def test_clamps_to_range(self) -> None:
        state = FixtureState(dimmer=0.8)

        # Clamp to 1.0
        delta = FixtureDelta(dimmer=(BlendOp.ADD_CLAMP, 0.5))
        assert apply_delta(state, delta)["dimmer"] == 1.0

        # Clamp to 0.0
        state = FixtureState(dimmer=0.2)
        delta = FixtureDelta(dimmer=(BlendOp.ADD_CLAMP, -0.5))
        assert apply_delta(state, delta)["dimmer"] == 0.0


class TestMergeDeltas:
    def test_compositing_order(self) -> None:
        """SET 0.5 → ADD 0.2 → MUL 0.5 = 0.35"""
        deltas = [
            FixtureDelta(dimmer=(BlendOp.SET, 0.5)),
            FixtureDelta(dimmer=(BlendOp.ADD_CLAMP, 0.2)),
            FixtureDelta(dimmer=(BlendOp.MUL, 0.5)),
        ]
        result = merge_deltas(deltas)
        assert result["dimmer"] == pytest.approx(0.35)

    def test_with_initial_state(self) -> None:
        """MUL operates on initial state."""
        initial = FixtureState(dimmer=0.8)
        delta = FixtureDelta(dimmer=(BlendOp.MUL, 0.5))
        result = merge_deltas([delta], initial)
        assert result["dimmer"] == pytest.approx(0.4)


class TestFixtureDeltaScale:
    def test_scale_scalar(self) -> None:
        delta = FixtureDelta(dimmer=(BlendOp.SET, 1.0))
        scaled = delta.scale(0.5)
        assert scaled["dimmer"] == (BlendOp.SET, 0.5)

    def test_scale_tuple(self) -> None:
        delta = FixtureDelta(color=(BlendOp.SET, (1.0, 0.8, 0.6)))
        scaled = delta.scale(0.5)
        assert scaled["color"][1] == pytest.approx((0.5, 0.4, 0.3))

    def test_scale_preserves_blend_op(self) -> None:
        delta = FixtureDelta(dimmer=(BlendOp.MUL, 0.8))
        scaled = delta.scale(0.5)
        assert scaled["dimmer"][0] == BlendOp.MUL

    def test_scale_returns_new_delta(self) -> None:
        delta = FixtureDelta(dimmer=(BlendOp.SET, 1.0))
        scaled = delta.scale(0.5)
        assert delta["dimmer"] == (BlendOp.SET, 1.0)
        assert scaled["dimmer"] == (BlendOp.SET, 0.5)


class TestScaleDeltas:
    def test_scales_all_fixtures(self) -> None:
        from dmxld.blend import scale_deltas
        from dmxld.attributes import DimmerAttr, RGBAttr
        from dmxld.model import Fixture, FixtureType

        FT = FixtureType(DimmerAttr(), RGBAttr())
        f1 = Fixture(FT, universe=1, address=1)
        f2 = Fixture(FT, universe=1, address=5)
        deltas = {
            f1: FixtureDelta(dimmer=(BlendOp.SET, 1.0)),
            f2: FixtureDelta(dimmer=(BlendOp.SET, 0.8)),
        }
        scaled = scale_deltas(deltas, 0.5)
        assert scaled[f1]["dimmer"] == (BlendOp.SET, 0.5)
        assert scaled[f2]["dimmer"] == (BlendOp.SET, pytest.approx(0.4))


class TestListValueHandling:
    """Ensure list values (from JSON) are handled like tuples."""

    def test_apply_op_list_set(self) -> None:
        from dmxld.blend import _apply_op
        result = _apply_op(None, BlendOp.SET, [1.0, 0.0, 0.0])
        assert result == pytest.approx((1.0, 0.0, 0.0))

    def test_apply_op_list_add_clamp(self) -> None:
        from dmxld.blend import _apply_op
        result = _apply_op((0.5, 0.5, 0.5), BlendOp.ADD_CLAMP, [0.3, 0.3, 0.3])
        assert result == pytest.approx((0.8, 0.8, 0.8))

    def test_scale_list_value(self) -> None:
        delta = FixtureDelta()
        delta["color"] = (BlendOp.SET, [1.0, 0.8, 0.6])
        scaled = delta.scale(0.5)
        assert scaled["color"][1] == pytest.approx((0.5, 0.4, 0.3))

    def test_scale_into_list_value(self) -> None:
        delta = FixtureDelta()
        delta["color"] = (BlendOp.SET, [1.0, 0.8, 0.6])
        out = FixtureDelta()
        delta.scale_into(0.5, out)
        assert out["color"][1] == pytest.approx((0.5, 0.4, 0.3))


class TestColorBoostPreservation:
    """Test that Color boost is preserved during scale operations."""

    def test_scale_preserves_color_type(self) -> None:
        # Create FixtureDelta with Color value
        delta = FixtureDelta(color=(BlendOp.SET, Color(1.0, 0.5, 0.0, boost=0.8)))

        # Scale it
        scaled = delta.scale(0.5)

        # Result should be a Color instance with preserved boost
        result_color = scaled["color"][1]
        assert isinstance(result_color, Color)
        assert result_color.boost == 0.8
        assert result_color == pytest.approx((0.5, 0.25, 0.0))

    def test_scale_into_preserves_color_type(self) -> None:
        # Create FixtureDelta with Color value
        delta = FixtureDelta(color=(BlendOp.SET, Color(1.0, 0.5, 0.0, boost=0.8)))

        # Scale into existing delta
        out = FixtureDelta()
        delta.scale_into(0.5, out)

        # Result should be a Color instance with preserved boost
        result_color = out["color"][1]
        assert isinstance(result_color, Color)
        assert result_color.boost == 0.8
        assert result_color == pytest.approx((0.5, 0.25, 0.0))

    def test_scale_plain_tuple_unchanged(self) -> None:
        # Verify plain tuples (not Color) still work as before
        delta = FixtureDelta(color=(BlendOp.SET, (1.0, 0.5, 0.0)))

        # Scale it
        scaled = delta.scale(0.5)

        # Result should be plain tuple, not Color
        result = scaled["color"][1]
        assert not isinstance(result, Color)
        assert isinstance(result, tuple)
        assert result == pytest.approx((0.5, 0.25, 0.0))

    def test_boost_preserved_through_merge_deltas(self) -> None:
        """Color.boost survives merge_deltas (the engine apply path)."""
        delta = FixtureDelta(color=(BlendOp.SET, Color(1.0, 0.0, 0.0, boost=0.8)))
        state = merge_deltas([delta])
        assert isinstance(state["color"], Color)
        assert state["color"].boost == 0.8

    def test_boost_preserved_through_apply_delta(self) -> None:
        """Color.boost survives apply_delta with existing state."""
        state = FixtureState(color=(0.5, 0.5, 0.5))
        delta = FixtureDelta(color=(BlendOp.SET, Color(1.0, 0.0, 0.0, boost=0.6)))
        result = apply_delta(state, delta)
        assert isinstance(result["color"], Color)
        assert result["color"].boost == 0.6

    def test_boost_max_on_add_clamp(self) -> None:
        """ADD_CLAMP takes max boost from both operands."""
        state = FixtureState(color=Color(0.5, 0.0, 0.0, boost=0.3))
        delta = FixtureDelta(color=(BlendOp.ADD_CLAMP, Color(0.0, 0.5, 0.0, boost=0.7)))
        result = apply_delta(state, delta)
        assert isinstance(result["color"], Color)
        assert result["color"].boost == 0.7
        assert result["color"] == pytest.approx((0.5, 0.5, 0.0))
