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


# Type for effect params function: (t, fixture, index, segment) -> FixtureState
EffectParamsFn = Callable[[float, Fixture, int, int], FixtureState]


@dataclass
class EffectClip:
    """Math-driven effect with access to time, fixture, index, and segment.

    The params function receives (t, fixture, index, segment) allowing per-fixture
    and per-segment effects based on time, position, or iteration order.

    For segmented fixtures (e.g., LED bars with multiple color zones), the params
    function is called once per segment. The segment index can be used to create
    per-segment animations. Non-segmented fixtures always have segment=0.

    Args:
        blend_op: How to combine with other clips (SET overwrites, MUL multiplies,
                  ADD_CLAMP adds). Defaults to SET. Use MUL to layer dimmer
                  modulation on top of other clips.

    Example - color wave across fixtures by X position:
        EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(
                dimmer=1.0,
                color=Color.from_hsv((t * 0.2 + f.pos.x * 0.1) % 1.0, 1.0, 1.0)
            ),
            clip_duration=10.0,
        )

    Example - rainbow across segments:
        EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(
                color=Color.from_hsv((t + seg * 0.25) % 1.0, 1.0, 1.0)
            ),
            clip_duration=10.0,
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
            delta = FixtureDelta()
            segment_count = fixture.segment_count

            for seg in range(segment_count):
                state = self.params(t, fixture, idx, seg)

                for name, value in state.items():
                    if name == "dimmer":
                        # Dimmer is fixture-level (only set on first segment)
                        if seg == 0:
                            delta[name] = (self.blend_op, value * fade_mult)
                    elif name == "color" and segment_count > 1:
                        # Map color to segment-indexed key for multi-segment fixtures
                        key = f"color_{seg}"
                        delta[key] = (self.blend_op, value)
                    else:
                        delta[name] = (self.blend_op, value)

            result[fixture] = delta
        return result
