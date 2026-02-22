"""Compositing logic for fixture states."""

from __future__ import annotations

from enum import Enum
from typing import Any

from dmxld.color import Color
from dmxld.model import FixtureState


class BlendOp(Enum):
    """Blend operation types."""

    SET = "set"
    ADD_CLAMP = "add_clamp"
    MUL = "mul"


class FixtureDelta(dict[str, tuple[BlendOp, Any]]):
    """Fixture delta. Just a dict with keyword constructor."""

    def __init__(self, **kwargs: tuple[BlendOp, Any]) -> None:
        super().__init__(kwargs)

    def __repr__(self) -> str:
        items = ", ".join(f"{k}={v!r}" for k, v in self.items())
        return f"FixtureDelta({items})"

    def scale(self, factor: float) -> FixtureDelta:
        """Return new FixtureDelta with all values scaled by factor."""
        result = FixtureDelta()
        for name, (op, value) in self.items():
            if isinstance(value, Color):
                result[name] = (op, Color(*(v * factor for v in value), boost=value.boost))
            elif isinstance(value, (tuple, list)):
                result[name] = (op, tuple(v * factor for v in value))
            elif isinstance(value, (int, float)):
                result[name] = (op, value * factor)
            else:
                result[name] = (op, value)
        return result

    def scale_into(self, factor: float, out: FixtureDelta) -> FixtureDelta:
        """Scale values into an existing FixtureDelta, reusing the object."""
        out.clear()
        for name, (op, value) in self.items():
            if isinstance(value, Color):
                out[name] = (op, Color(*(v * factor for v in value), boost=value.boost))
            elif isinstance(value, (tuple, list)):
                out[name] = (op, tuple(v * factor for v in value))
            elif isinstance(value, (int, float)):
                out[name] = (op, value * factor)
            else:
                out[name] = (op, value)
        return out


def _clamp(v: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, v))


def _apply_scalar_op(current: float, op: BlendOp, value: float) -> float:
    if op == BlendOp.SET:
        return value
    if op == BlendOp.ADD_CLAMP:
        return _clamp(current + value)
    if op == BlendOp.MUL:
        return _clamp(current * value)
    return current


def _apply_tuple_op(
    current: tuple[float, ...],
    op: BlendOp,
    value: tuple[float, ...],
) -> tuple[float, ...]:
    result = tuple(_apply_scalar_op(c, op, v) for c, v in zip(current, value))
    boost = max(getattr(current, 'boost', 0.0), getattr(value, 'boost', 0.0))
    if boost > 0:
        return Color(*result, boost=boost)
    return result


def _apply_op(current: Any, op: BlendOp, value: Any) -> Any:
    """Apply blend operation to a value."""
    if isinstance(value, (int, float)):
        current_val = float(current) if current is not None else 0.0
        return _apply_scalar_op(current_val, op, float(value))
    elif isinstance(value, (tuple, list)):
        if current is None:
            current = tuple(0.0 for _ in value)
        return _apply_tuple_op(current, op, value)
    else:
        # Unknown type, SET overwrites, others keep current
        return value if op == BlendOp.SET else current


def apply_delta(state: FixtureState, delta: FixtureDelta) -> FixtureState:
    """Apply a delta to a state, returning new state."""
    new_state = state.copy()
    for name, (op, value) in delta.items():
        current = new_state.get(name)
        new_value = _apply_op(current, op, value)
        new_state[name] = new_value
    return new_state


def merge_deltas(
    deltas: list[FixtureDelta], initial: FixtureState | None = None
) -> FixtureState:
    """Merge multiple deltas into a final state."""
    state = initial.copy() if initial else FixtureState()
    for delta in deltas:
        state = apply_delta(state, delta)
    return state


def scale_deltas(deltas: dict, factor: float) -> dict:
    """Scale all FixtureDelta values in a deltas dict by factor."""
    return {target: delta.scale(factor) for target, delta in deltas.items()}


def scale_deltas_into(deltas: dict, factor: float, out: dict) -> dict:
    """Scale all FixtureDelta values into pre-allocated output dict."""
    for target, delta in deltas.items():
        if target not in out:
            out[target] = FixtureDelta()
        delta.scale_into(factor, out[target])
    return out
