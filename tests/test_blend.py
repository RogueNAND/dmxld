"""Tests for blend operations and delta compositing."""

import pytest

from dmxld.blend import BlendOp, FixtureDelta, apply_delta, merge_deltas
from dmxld.model import FixtureState


class TestBlendOps:
    """Core blend operation behaviors."""

    def test_set_overwrites(self) -> None:
        state = FixtureState(dimmer=0.5)
        delta = FixtureDelta(dimmer=(BlendOp.SET, 0.8))
        result = apply_delta(state, delta)
        assert result.get("dimmer") == 0.8

    def test_mul_multiplies(self) -> None:
        state = FixtureState(dimmer=0.8)
        delta = FixtureDelta(dimmer=(BlendOp.MUL, 0.5))
        result = apply_delta(state, delta)
        assert result.get("dimmer") == pytest.approx(0.4)

    def test_add_clamp_adds(self) -> None:
        state = FixtureState(dimmer=0.3)
        delta = FixtureDelta(dimmer=(BlendOp.ADD_CLAMP, 0.4))
        result = apply_delta(state, delta)
        assert result.get("dimmer") == pytest.approx(0.7)

    def test_rgb_blending(self) -> None:
        """Tuple values blend component-wise."""
        state = FixtureState(rgb=(1.0, 0.8, 0.6))
        delta = FixtureDelta(rgb=(BlendOp.MUL, (0.5, 0.5, 0.5)))
        result = apply_delta(state, delta)
        rgb = result.get("rgb")
        assert rgb[0] == pytest.approx(0.5)
        assert rgb[1] == pytest.approx(0.4)
        assert rgb[2] == pytest.approx(0.3)


class TestClamping:
    """Values are clamped to 0.0-1.0 range."""

    def test_clamps_to_one(self) -> None:
        state = FixtureState(dimmer=0.8)
        delta = FixtureDelta(dimmer=(BlendOp.ADD_CLAMP, 0.5))
        result = apply_delta(state, delta)
        assert result.get("dimmer") == 1.0

    def test_clamps_to_zero(self) -> None:
        state = FixtureState(dimmer=0.2)
        delta = FixtureDelta(dimmer=(BlendOp.ADD_CLAMP, -0.5))
        result = apply_delta(state, delta)
        assert result.get("dimmer") == 0.0


class TestMergeDeltas:
    """Compositing multiple deltas in order."""

    def test_compositing_order(self) -> None:
        """Operations apply in order: SET 0.5 -> ADD 0.2 -> MUL 0.5 = 0.35"""
        delta1 = FixtureDelta(dimmer=(BlendOp.SET, 0.5))
        delta2 = FixtureDelta(dimmer=(BlendOp.ADD_CLAMP, 0.2))
        delta3 = FixtureDelta(dimmer=(BlendOp.MUL, 0.5))
        result = merge_deltas([delta1, delta2, delta3])
        # 0.5 + 0.2 = 0.7, then 0.7 * 0.5 = 0.35
        assert result.get("dimmer") == pytest.approx(0.35)

    def test_last_set_wins(self) -> None:
        """Multiple SETs - last one wins."""
        delta1 = FixtureDelta(dimmer=(BlendOp.SET, 0.3))
        delta2 = FixtureDelta(dimmer=(BlendOp.SET, 0.9))
        result = merge_deltas([delta1, delta2])
        assert result.get("dimmer") == 0.9

    def test_with_initial_state(self) -> None:
        """MUL operates on initial state when no SET precedes."""
        initial = FixtureState(dimmer=0.8)
        delta = FixtureDelta(dimmer=(BlendOp.MUL, 0.5))
        result = merge_deltas([delta], initial)
        assert result.get("dimmer") == pytest.approx(0.4)
