"""Tests for blend operations and delta compositing."""

import pytest

from dmxld.blend import BlendOp, FixtureDelta, apply_delta, merge_deltas
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
