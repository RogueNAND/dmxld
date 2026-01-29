"""Clip system for dmxld."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Iterable, Protocol, runtime_checkable

from dmxld.blend import BlendOp, FixtureDelta, merge_deltas
from dmxld.model import Fixture, FixtureState, Rig


@runtime_checkable
class Clip(Protocol):
    @property
    def duration(self) -> float | None:
        """Duration in seconds, or None for infinite."""
        ...

    def render(self, t: float, rig: Rig) -> dict[Fixture, FixtureDelta]:
        ...


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

    _selector: Selector = field(init=False, repr=False)
    _params_fn: ParamsFn = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if callable(self.selector):
            self._selector = self.selector
        else:
            fixtures = list(self.selector)
            self._selector = lambda rig: fixtures

        if callable(self.params_fn):
            self._params_fn = self.params_fn
        else:
            state = self.params_fn
            self._params_fn = lambda fixture: state

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

        result: dict[Fixture, FixtureDelta] = {}
        for fixture in self._selector(rig):
            state = self._params_fn(fixture)
            result[fixture] = FixtureDelta(
                dimmer=(BlendOp.SET, state.dimmer * fade_mult),
                rgb=(BlendOp.SET, state.rgb),
            )
        return result


@dataclass
class DimmerPulseClip:
    """Sine wave pulse on dimmer channel."""

    selector: Selector | Iterable[Fixture]
    rate_hz: float = 1.0
    depth: float = 0.5
    base: float = 0.5
    clip_duration: float | None = None

    _selector: Selector = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if callable(self.selector):
            self._selector = self.selector
        else:
            fixtures = list(self.selector)
            self._selector = lambda rig: fixtures

    @property
    def duration(self) -> float | None:
        return self.clip_duration

    def render(self, t: float, rig: Rig) -> dict[Fixture, FixtureDelta]:
        if t < 0 or (self.clip_duration is not None and t > self.clip_duration):
            return {}

        phase = t * self.rate_hz * 2 * math.pi
        pulse_value = max(0.0, min(1.0, self.base + self.depth * math.sin(phase)))

        result: dict[Fixture, FixtureDelta] = {}
        for fixture in self._selector(rig):
            result[fixture] = FixtureDelta(
                dimmer=(BlendOp.MUL, pulse_value),
            )
        return result


@dataclass
class TimelineClip:
    """Timeline with scheduled clips."""

    events: list[tuple[float, Clip]] = field(default_factory=list)

    @property
    def duration(self) -> float | None:
        if not self.events:
            return 0.0
        max_end: float = 0.0
        for start_time, clip in self.events:
            clip_dur = clip.duration
            if clip_dur is None:
                return None
            max_end = max(max_end, start_time + clip_dur)
        return max_end

    def add(self, start_time: float, clip: Clip) -> TimelineClip:
        self.events.append((start_time, clip))
        return self

    def render(self, t: float, rig: Rig) -> dict[Fixture, FixtureDelta]:
        fixture_deltas: dict[Fixture, list[FixtureDelta]] = {}

        for start_time, clip in self.events:
            local_t = t - start_time
            if local_t < 0:
                continue
            if clip.duration is not None and local_t > clip.duration:
                continue

            deltas = clip.render(local_t, rig)
            for fixture, delta in deltas.items():
                fixture_deltas.setdefault(fixture, []).append(delta)

        result: dict[Fixture, FixtureDelta] = {}
        for fixture, deltas in fixture_deltas.items():
            merged = merge_deltas(deltas)
            result[fixture] = FixtureDelta(
                dimmer=(BlendOp.SET, merged.dimmer),
                rgb=(BlendOp.SET, merged.rgb),
            )
        return result
