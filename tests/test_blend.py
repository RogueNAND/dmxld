"""Unit tests for blend operations."""

import pytest

from dmxld.blend import BlendOp, FixtureDelta, apply_delta, merge_deltas
from dmxld.model import FixtureState


class TestBlendOpSet:
    """Tests for BlendOp.SET behavior."""

    def test_set_dimmer_overwrites(self) -> None:
        state = FixtureState(dimmer=0.5, rgb=(1.0, 1.0, 1.0))
        delta = FixtureDelta(dimmer=(BlendOp.SET, 0.8))
        result = apply_delta(state, delta)
        assert result.dimmer == 0.8
        assert result.rgb == (1.0, 1.0, 1.0)

    def test_set_rgb_overwrites(self) -> None:
        state = FixtureState(dimmer=1.0, rgb=(0.5, 0.5, 0.5))
        delta = FixtureDelta(rgb=(BlendOp.SET, (1.0, 0.0, 0.0)))
        result = apply_delta(state, delta)
        assert result.dimmer == 1.0
        assert result.rgb == (1.0, 0.0, 0.0)

    def test_set_both(self) -> None:
        state = FixtureState(dimmer=0.0, rgb=(0.0, 0.0, 0.0))
        delta = FixtureDelta(
            dimmer=(BlendOp.SET, 1.0),
            rgb=(BlendOp.SET, (0.5, 0.6, 0.7)),
        )
        result = apply_delta(state, delta)
        assert result.dimmer == 1.0
        assert result.rgb == (0.5, 0.6, 0.7)


class TestBlendOpMul:
    """Tests for BlendOp.MUL behavior."""

    def test_mul_dimmer(self) -> None:
        state = FixtureState(dimmer=0.8, rgb=(1.0, 1.0, 1.0))
        delta = FixtureDelta(dimmer=(BlendOp.MUL, 0.5))
        result = apply_delta(state, delta)
        assert result.dimmer == pytest.approx(0.4)

    def test_mul_rgb(self) -> None:
        state = FixtureState(dimmer=1.0, rgb=(1.0, 0.8, 0.6))
        delta = FixtureDelta(rgb=(BlendOp.MUL, (0.5, 0.5, 0.5)))
        result = apply_delta(state, delta)
        assert result.rgb[0] == pytest.approx(0.5)
        assert result.rgb[1] == pytest.approx(0.4)
        assert result.rgb[2] == pytest.approx(0.3)

    def test_mul_clamps_to_zero(self) -> None:
        state = FixtureState(dimmer=0.5, rgb=(0.5, 0.5, 0.5))
        delta = FixtureDelta(dimmer=(BlendOp.MUL, -1.0))
        result = apply_delta(state, delta)
        assert result.dimmer == 0.0

    def test_mul_clamps_to_one(self) -> None:
        state = FixtureState(dimmer=0.5, rgb=(0.5, 0.5, 0.5))
        delta = FixtureDelta(dimmer=(BlendOp.MUL, 3.0))
        result = apply_delta(state, delta)
        assert result.dimmer == 1.0


class TestBlendOpAddClamp:
    """Tests for BlendOp.ADD_CLAMP behavior."""

    def test_add_dimmer(self) -> None:
        state = FixtureState(dimmer=0.3, rgb=(0.0, 0.0, 0.0))
        delta = FixtureDelta(dimmer=(BlendOp.ADD_CLAMP, 0.4))
        result = apply_delta(state, delta)
        assert result.dimmer == pytest.approx(0.7)

    def test_add_rgb(self) -> None:
        state = FixtureState(dimmer=1.0, rgb=(0.2, 0.3, 0.4))
        delta = FixtureDelta(rgb=(BlendOp.ADD_CLAMP, (0.1, 0.2, 0.3)))
        result = apply_delta(state, delta)
        assert result.rgb[0] == pytest.approx(0.3)
        assert result.rgb[1] == pytest.approx(0.5)
        assert result.rgb[2] == pytest.approx(0.7)

    def test_add_clamps_at_one(self) -> None:
        state = FixtureState(dimmer=0.8, rgb=(0.9, 0.9, 0.9))
        delta = FixtureDelta(
            dimmer=(BlendOp.ADD_CLAMP, 0.5),
            rgb=(BlendOp.ADD_CLAMP, (0.5, 0.5, 0.5)),
        )
        result = apply_delta(state, delta)
        assert result.dimmer == 1.0
        assert result.rgb == (1.0, 1.0, 1.0)

    def test_add_clamps_at_zero(self) -> None:
        state = FixtureState(dimmer=0.2, rgb=(0.1, 0.1, 0.1))
        delta = FixtureDelta(
            dimmer=(BlendOp.ADD_CLAMP, -0.5),
            rgb=(BlendOp.ADD_CLAMP, (-0.5, -0.5, -0.5)),
        )
        result = apply_delta(state, delta)
        assert result.dimmer == 0.0
        assert result.rgb == (0.0, 0.0, 0.0)


class TestMergeDeltas:
    """Tests for merge_deltas compositing."""

    def test_empty_deltas(self) -> None:
        result = merge_deltas([])
        assert result.dimmer == 0.0
        assert result.rgb == (0.0, 0.0, 0.0)

    def test_single_delta(self) -> None:
        delta = FixtureDelta(
            dimmer=(BlendOp.SET, 0.5),
            rgb=(BlendOp.SET, (1.0, 0.0, 0.0)),
        )
        result = merge_deltas([delta])
        assert result.dimmer == 0.5
        assert result.rgb == (1.0, 0.0, 0.0)

    def test_compositing_order_set_then_mul(self) -> None:
        delta1 = FixtureDelta(dimmer=(BlendOp.SET, 1.0))
        delta2 = FixtureDelta(dimmer=(BlendOp.MUL, 0.5))
        result = merge_deltas([delta1, delta2])
        assert result.dimmer == pytest.approx(0.5)

    def test_compositing_order_mul_then_set(self) -> None:
        delta1 = FixtureDelta(dimmer=(BlendOp.MUL, 0.5))
        delta2 = FixtureDelta(dimmer=(BlendOp.SET, 1.0))
        result = merge_deltas([delta1, delta2])
        assert result.dimmer == 1.0

    def test_compositing_set_add_mul(self) -> None:
        delta1 = FixtureDelta(dimmer=(BlendOp.SET, 0.5))
        delta2 = FixtureDelta(dimmer=(BlendOp.ADD_CLAMP, 0.2))
        delta3 = FixtureDelta(dimmer=(BlendOp.MUL, 0.5))
        result = merge_deltas([delta1, delta2, delta3])
        assert result.dimmer == pytest.approx(0.35)

    def test_with_initial_state(self) -> None:
        initial = FixtureState(dimmer=0.8, rgb=(1.0, 1.0, 1.0))
        delta = FixtureDelta(dimmer=(BlendOp.MUL, 0.5))
        result = merge_deltas([delta], initial)
        assert result.dimmer == pytest.approx(0.4)
        assert result.rgb == (1.0, 1.0, 1.0)

    def test_last_set_wins(self) -> None:
        delta1 = FixtureDelta(dimmer=(BlendOp.SET, 0.3))
        delta2 = FixtureDelta(dimmer=(BlendOp.SET, 0.7))
        delta3 = FixtureDelta(dimmer=(BlendOp.SET, 0.9))
        result = merge_deltas([delta1, delta2, delta3])
        assert result.dimmer == 0.9
