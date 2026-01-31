"""Clip system for dmxld."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

from dmxld.blend import BlendOp, FixtureDelta
from dmxld.model import Fixture, FixtureState, Rig


class Clip(Protocol):
    """Protocol for clips that can be rendered."""

    @property
    def duration(self) -> float | None:
        """Duration in seconds, or None for infinite."""
        ...

    def render(self, t: float, rig: Rig) -> dict[Fixture, FixtureDelta]:
        """Render the clip at time t, returning deltas for affected fixtures."""
        ...


Selector = Callable[[Rig], Iterable[Fixture]]
ParamsFn = Callable[[Fixture], FixtureState]


@dataclass
class SceneClip:
    """Static scene with optional fade in/out.

    Args:
        blend_op: How to combine with other clips (SET overwrites, MUL multiplies,
                  ADD_CLAMP adds). Defaults to SET.
    """

    selector: Selector | Iterable[Fixture]
    params: ParamsFn | FixtureState
    fade_in: float = 0.0
    fade_out: float = 0.0
    clip_duration: float | None = None
    blend_op: BlendOp = BlendOp.SET

    @property
    def duration(self) -> float | None:
        return self.clip_duration

    def render(self, t: float, rig: Rig) -> dict[Fixture, FixtureDelta]:
        if t < 0 or (self.clip_duration is not None and t > self.clip_duration):
            return {}

        fade_mult = 1.0
        if self.fade_in > 0 and t < self.fade_in:
            fade_mult = t / self.fade_in
        elif self.clip_duration is not None and self.fade_out > 0:
            time_remaining = self.clip_duration - t
            if time_remaining < self.fade_out:
                fade_mult = max(0.0, time_remaining / self.fade_out)

        selector_fn = self.selector if callable(self.selector) else lambda r: self.selector
        params_fn = self.params if callable(self.params) else lambda f: self.params

        result: dict[Fixture, FixtureDelta] = {}
        for fixture in selector_fn(rig):
            state = params_fn(fixture)
            delta = FixtureDelta()
            for name, value in state.items():
                if name == "dimmer":
                    delta[name] = (self.blend_op, value * fade_mult)
                else:
                    delta[name] = (self.blend_op, value)
            result[fixture] = delta
        return result


# Type for effect params function: (t, fixture, index) -> FixtureState
EffectParamsFn = Callable[[float, Fixture, int], FixtureState]


@dataclass
class EffectClip:
    """Math-driven effect with access to time, fixture, and index.

    The params function receives (t, fixture, index) allowing per-fixture
    effects based on time, position, or iteration order.

    Args:
        blend_op: How to combine with other clips (SET overwrites, MUL multiplies,
                  ADD_CLAMP adds). Defaults to SET. Use MUL to layer dimmer
                  modulation on top of other clips.

    Example - color wave across fixtures by X position:
        EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i: FixtureState(
                dimmer=1.0,
                rgb=hsv_to_rgb((t * 0.2 + f.pos.x * 0.1) % 1.0, 1.0, 1.0)
            ),
            clip_duration=10.0,
        )

    Example - dimmer pulse layered on top (using MUL):
        EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i: FixtureState(
                dimmer=0.5 + 0.5 * math.sin(t * 2 * math.pi)
            ),
            clip_duration=10.0,
            blend_op=BlendOp.MUL,
        )
    """

    selector: Selector | Iterable[Fixture]
    params: EffectParamsFn
    fade_in: float = 0.0
    fade_out: float = 0.0
    clip_duration: float | None = None
    blend_op: BlendOp = BlendOp.SET

    @property
    def duration(self) -> float | None:
        return self.clip_duration

    def render(self, t: float, rig: Rig) -> dict[Fixture, FixtureDelta]:
        if t < 0 or (self.clip_duration is not None and t > self.clip_duration):
            return {}

        fade_mult = 1.0
        if self.fade_in > 0 and t < self.fade_in:
            fade_mult = t / self.fade_in
        elif self.clip_duration is not None and self.fade_out > 0:
            time_remaining = self.clip_duration - t
            if time_remaining < self.fade_out:
                fade_mult = max(0.0, time_remaining / self.fade_out)

        selector_fn = self.selector if callable(self.selector) else lambda r: self.selector

        result: dict[Fixture, FixtureDelta] = {}
        for idx, fixture in enumerate(selector_fn(rig)):
            state = self.params(t, fixture, idx)
            delta = FixtureDelta()
            for name, value in state.items():
                if name == "dimmer":
                    delta[name] = (self.blend_op, value * fade_mult)
                else:
                    delta[name] = (self.blend_op, value)
            result[fixture] = delta
        return result
