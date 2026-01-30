"""Generic clip protocol and timeline scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Generic, Protocol, TypeVar, runtime_checkable

Ctx = TypeVar("Ctx")
Target = TypeVar("Target")
Delta = TypeVar("Delta")

ComposeFn = Callable[[list[Delta]], Delta]


@runtime_checkable
class Clip(Protocol[Ctx, Target, Delta]):
    """Generic clip protocol."""

    @property
    def duration(self) -> float | None:
        ...

    def render(self, t: float, ctx: Ctx) -> dict[Target, Delta]:
        ...


@dataclass
class Timeline(Generic[Ctx, Target, Delta]):
    """Timeline that schedules clips."""

    compose_fn: ComposeFn[Delta]
    events: list[tuple[float, Clip[Ctx, Target, Delta]]] = field(default_factory=list)

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

    def add(
        self, start_time: float, clip: Clip[Ctx, Target, Delta]
    ) -> Timeline[Ctx, Target, Delta]:
        self.events.append((start_time, clip))
        return self

    def render(self, t: float, ctx: Ctx) -> dict[Target, Delta]:
        target_deltas: dict[Target, list[Delta]] = {}

        for start_time, clip in self.events:
            local_t = t - start_time
            if local_t < 0:
                continue
            if clip.duration is not None and local_t > clip.duration:
                continue

            deltas = clip.render(local_t, ctx)
            for target, delta in deltas.items():
                target_deltas.setdefault(target, []).append(delta)

        result: dict[Target, Delta] = {}
        for target, deltas in target_deltas.items():
            result[target] = self.compose_fn(deltas)
        return result
