"""Compositing logic for fixture states."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fcld.model import FixtureState


class BlendOp(Enum):
    """Blend operation types."""

    SET = "set"
    ADD_CLAMP = "add_clamp"
    MUL = "mul"


@dataclass
class FixtureDelta:
    """A change to apply to a fixture state."""

    dimmer: tuple[BlendOp, float] | None = None
    rgb: tuple[BlendOp, tuple[float, float, float]] | None = None


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _apply_op(current: float, op: BlendOp, value: float) -> float:
    if op == BlendOp.SET:
        return value
    if op == BlendOp.ADD_CLAMP:
        return _clamp(current + value)
    if op == BlendOp.MUL:
        return _clamp(current * value)
    return current


def _apply_rgb_op(
    current: tuple[float, float, float],
    op: BlendOp,
    value: tuple[float, float, float],
) -> tuple[float, float, float]:
    return (
        _apply_op(current[0], op, value[0]),
        _apply_op(current[1], op, value[1]),
        _apply_op(current[2], op, value[2]),
    )


def apply_delta(state: FixtureState, delta: FixtureDelta) -> FixtureState:
    """Apply a single delta to a fixture state, returning a new state."""
    new_dimmer = state.dimmer
    new_rgb = state.rgb

    if delta.dimmer is not None:
        op, value = delta.dimmer
        new_dimmer = _apply_op(state.dimmer, op, value)

    if delta.rgb is not None:
        op, value = delta.rgb
        new_rgb = _apply_rgb_op(state.rgb, op, value)

    return FixtureState(dimmer=new_dimmer, rgb=new_rgb)


def merge_deltas(deltas: list[FixtureDelta], initial: FixtureState | None = None) -> FixtureState:
    """Compose multiple deltas in order, returning the final state."""
    state = initial.copy() if initial else FixtureState()
    for delta in deltas:
        state = apply_delta(state, delta)
    return state
