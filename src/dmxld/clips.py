"""Clip system for dmxld."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Iterable

from timeline import Clip as GenericClip, Timeline

from dmxld.blend import BlendOp, FixtureDelta, compose_lighting_deltas
from dmxld.model import Fixture, FixtureState, Rig

# Type alias for lighting-specific clips
Clip = GenericClip[Rig, Fixture, FixtureDelta]


Selector = Callable[[Rig], Iterable[Fixture]]
ParamsFn = Callable[[Fixture], FixtureState]


@dataclass
class SceneClip:
    """Static scene with optional fade in/out."""

    selector: Selector | Iterable[Fixture]
    params_fn: ParamsFn | FixtureState
    fade_in: float = 0.0
    fade_out: float = 0.0
    clip_duration: float | None = None

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
        params_fn = self.params_fn if callable(self.params_fn) else lambda f: self.params_fn

        result: dict[Fixture, FixtureDelta] = {}
        for fixture in selector_fn(rig):
            state = params_fn(fixture)
            delta = FixtureDelta()
            for name, value in state.items():
                if name == "dimmer":
                    delta[name] = (BlendOp.SET, value * fade_mult)
                else:
                    delta[name] = (BlendOp.SET, value)
            result[fixture] = delta
        return result


@dataclass
class DimmerPulseClip:
    """Sine wave pulse on dimmer channel."""

    selector: Selector | Iterable[Fixture]
    rate_hz: float = 1.0
    depth: float = 0.5
    base: float = 0.5
    clip_duration: float | None = None

    @property
    def duration(self) -> float | None:
        return self.clip_duration

    def render(self, t: float, rig: Rig) -> dict[Fixture, FixtureDelta]:
        if t < 0 or (self.clip_duration is not None and t > self.clip_duration):
            return {}

        phase = t * self.rate_hz * 2 * math.pi
        pulse_value = max(0.0, min(1.0, self.base + self.depth * math.sin(phase)))

        selector_fn = self.selector if callable(self.selector) else lambda r: self.selector
        result: dict[Fixture, FixtureDelta] = {}
        for fixture in selector_fn(rig):
            delta = FixtureDelta()
            delta["dimmer"] = (BlendOp.MUL, pulse_value)
            result[fixture] = delta
        return result


LightingTimeline = Timeline[Rig, Fixture, FixtureDelta]


def TimelineClip() -> LightingTimeline:
    """Create a timeline for lighting clips."""
    return Timeline(compose_fn=compose_lighting_deltas)
