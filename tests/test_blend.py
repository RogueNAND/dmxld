"""Tests for blend operations and delta compositing."""

import pytest

from dmxld.blend import BlendOp, FixtureDelta, apply_delta, merge_deltas, compose_add, compose_override
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


class TestColorBoostScaling:
    """Test that Color boost scales proportionally during operations."""

    def test_scale_scales_boost(self) -> None:
        # Boost should scale with the factor, not be preserved
        delta = FixtureDelta(color=(BlendOp.SET, Color(1.0, 0.5, 0.0, boost=0.8)))
        scaled = delta.scale(0.5)

        result_color = scaled["color"][1]
        assert isinstance(result_color, Color)
        assert result_color.boost == pytest.approx(0.4)
        assert result_color == pytest.approx((0.5, 0.25, 0.0))

    def test_scale_into_scales_boost(self) -> None:
        delta = FixtureDelta(color=(BlendOp.SET, Color(1.0, 0.5, 0.0, boost=0.8)))
        out = FixtureDelta()
        delta.scale_into(0.5, out)

        result_color = out["color"][1]
        assert isinstance(result_color, Color)
        assert result_color.boost == pytest.approx(0.4)
        assert result_color == pytest.approx((0.5, 0.25, 0.0))

    def test_scale_plain_tuple_unchanged(self) -> None:
        # Verify plain tuples (not Color) still work as before
        delta = FixtureDelta(color=(BlendOp.SET, (1.0, 0.5, 0.0)))
        scaled = delta.scale(0.5)

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
        """Color.boost survives apply_delta with SET op."""
        state = FixtureState(color=(0.5, 0.5, 0.5))
        delta = FixtureDelta(color=(BlendOp.SET, Color(1.0, 0.0, 0.0, boost=0.6)))
        result = apply_delta(state, delta)
        assert isinstance(result["color"], Color)
        assert result["color"].boost == 0.6

    def test_boost_summed_on_add_clamp(self) -> None:
        """ADD_CLAMP sums boost from both operands (clamped to 1.0)."""
        state = FixtureState(color=Color(0.5, 0.0, 0.0, boost=0.3))
        delta = FixtureDelta(color=(BlendOp.ADD_CLAMP, Color(0.0, 0.5, 0.0, boost=0.7)))
        result = apply_delta(state, delta)
        assert isinstance(result["color"], Color)
        assert result["color"].boost == pytest.approx(1.0)
        assert result["color"] == pytest.approx((0.5, 0.5, 0.0))

    def test_boost_sum_clamped_to_one(self) -> None:
        """Boost sum is clamped to 1.0."""
        state = FixtureState(color=Color(0.5, 0.0, 0.0, boost=0.8))
        delta = FixtureDelta(color=(BlendOp.ADD_CLAMP, Color(0.0, 0.5, 0.0, boost=0.9)))
        result = apply_delta(state, delta)
        assert result["color"].boost == 1.0

    def test_set_uses_incoming_boost_only(self) -> None:
        """SET op uses the incoming value's boost, ignoring current."""
        state = FixtureState(color=Color(0.5, 0.0, 0.0, boost=0.9))
        delta = FixtureDelta(color=(BlendOp.SET, Color(1.0, 0.0, 0.0, boost=0.2)))
        result = apply_delta(state, delta)
        assert result["color"].boost == 0.2

    def test_near_zero_fade_produces_near_zero_boost(self) -> None:
        """A clip at near-zero fade contributes negligible boost."""
        delta = FixtureDelta(color=(BlendOp.SET, Color(1.0, 0.0, 0.0, boost=0.5)))
        scaled = delta.scale(0.01)  # 1% fade
        result = scaled["color"][1]
        assert result.boost == pytest.approx(0.005)

    def test_zero_boost_stays_zero_through_scale(self) -> None:
        """Colors without boost remain plain tuples after scale."""
        delta = FixtureDelta(color=(BlendOp.SET, Color(1.0, 0.0, 0.0, boost=0.0)))
        scaled = delta.scale(0.5)
        result = scaled["color"][1]
        # boost=0 * 0.5 = 0, so Color is created but boost stays 0
        assert result.boost == 0.0


class TestComposeAdd:
    def test_different_attributes_merged(self) -> None:
        d1 = FixtureDelta(dimmer=(BlendOp.SET, 0.5))
        d2 = FixtureDelta(color=(BlendOp.SET, (1.0, 0.0, 0.0)))
        result = compose_add([d1, d2])
        assert result["dimmer"] == (BlendOp.SET, 0.5)
        assert result["color"] == (BlendOp.SET, (1.0, 0.0, 0.0))

    def test_same_numeric_attribute_summed(self) -> None:
        d1 = FixtureDelta(strobe=(BlendOp.SET, 0.3))
        d2 = FixtureDelta(strobe=(BlendOp.SET, 0.4))
        result = compose_add([d1, d2])
        assert result["strobe"] == (BlendOp.SET, pytest.approx(0.7))

    def test_dimmer_uses_htp(self) -> None:
        d1 = FixtureDelta(dimmer=(BlendOp.SET, 0.8))
        d2 = FixtureDelta(dimmer=(BlendOp.SET, 0.5))
        result = compose_add([d1, d2])
        assert result["dimmer"] == (BlendOp.SET, 0.8)

    def test_tuple_attributes_summed_elementwise(self) -> None:
        d1 = FixtureDelta(color=(BlendOp.SET, (0.5, 0.0, 0.0)))
        d2 = FixtureDelta(color=(BlendOp.SET, (0.0, 0.3, 0.2)))
        result = compose_add([d1, d2])
        assert result["color"][1] == pytest.approx((0.5, 0.3, 0.2))

    def test_color_boost_summed(self) -> None:
        """compose_add sums boost values (clamped to 1.0) for smooth transitions."""
        d1 = FixtureDelta(color=(BlendOp.SET, Color(0.5, 0.0, 0.0, boost=0.3)))
        d2 = FixtureDelta(color=(BlendOp.SET, Color(0.0, 0.5, 0.0, boost=0.7)))
        result = compose_add([d1, d2])
        val = result["color"][1]
        assert isinstance(val, Color)
        assert val.boost == pytest.approx(1.0)
        assert val == pytest.approx((0.5, 0.5, 0.0))

    def test_color_boost_smooth_fadein(self) -> None:
        """Near-zero contribution adds near-zero boost (no brightness jump)."""
        # Clip A at full fade: boost=0.0
        d1 = FixtureDelta(color=(BlendOp.SET, Color(1.0, 1.0, 1.0, boost=0.0)))
        # Clip B at 1% fade with boost=0.5: after scale, boost should be ~0.005
        d2 = FixtureDelta(color=(BlendOp.SET, Color(0.01, 0.0, 0.0, boost=0.005)))
        result = compose_add([d1, d2])
        val = result["color"][1]
        assert isinstance(val, Color)
        # Boost should be ~0.005, not 0.5 (the old max() behavior)
        assert val.boost == pytest.approx(0.005)

    def test_color_boost_sum_clamped(self) -> None:
        """Boost sum clamps to 1.0."""
        d1 = FixtureDelta(color=(BlendOp.SET, Color(0.5, 0.0, 0.0, boost=0.8)))
        d2 = FixtureDelta(color=(BlendOp.SET, Color(0.0, 0.5, 0.0, boost=0.6)))
        result = compose_add([d1, d2])
        val = result["color"][1]
        assert val.boost == 1.0

    def test_single_delta_returned_as_is(self) -> None:
        d = FixtureDelta(dimmer=(BlendOp.SET, 0.5))
        result = compose_add([d])
        assert result is d


class TestComposeOverride:
    def test_later_overwrites_earlier(self) -> None:
        d1 = FixtureDelta(dimmer=(BlendOp.SET, 0.5))
        d2 = FixtureDelta(dimmer=(BlendOp.SET, 0.8))
        result = compose_override([d1, d2])
        assert result["dimmer"] == (BlendOp.SET, 0.8)

    def test_non_overlapping_merged(self) -> None:
        d1 = FixtureDelta(dimmer=(BlendOp.SET, 0.5))
        d2 = FixtureDelta(color=(BlendOp.SET, (1.0, 0.0, 0.0)))
        result = compose_override([d1, d2])
        assert result["dimmer"] == (BlendOp.SET, 0.5)
        assert result["color"] == (BlendOp.SET, (1.0, 0.0, 0.0))

    def test_single_delta_returned_as_is(self) -> None:
        d = FixtureDelta(dimmer=(BlendOp.SET, 0.5))
        result = compose_override([d])
        assert result is d
