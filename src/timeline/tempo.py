"""BPM and tempo mapping for timeline scheduling."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic

from timeline.clip import Clip, ComposeFn, Ctx, Delta, Target


@dataclass
class TempoMap:
    """Maps beats to seconds with support for tempo changes."""

    _changes: list[tuple[float, float]] = field(default_factory=list)

    def __init__(self, bpm: float = 120.0):
        self._changes = [(0.0, bpm)]

    def set_tempo(self, beat: float, bpm: float) -> TempoMap:
        """Set tempo at a specific beat position. Chainable."""
        if beat <= 0:
            self._changes[0] = (0.0, bpm)
        else:
            self._changes.append((beat, bpm))
            self._changes.sort(key=lambda x: x[0])
        return self

    def time(self, beats: float) -> float:
        """Convert beat position to seconds."""
        if beats <= 0:
            return 0.0

        total_seconds = 0.0
        prev_beat = 0.0
        prev_bpm = self._changes[0][1]

        for change_beat, change_bpm in self._changes[1:]:
            if beats <= change_beat:
                break
            segment_beats = change_beat - prev_beat
            total_seconds += segment_beats * (60.0 / prev_bpm)
            prev_beat = change_beat
            prev_bpm = change_bpm

        remaining_beats = beats - prev_beat
        total_seconds += remaining_beats * (60.0 / prev_bpm)
        return total_seconds

    def beat(self, seconds: float) -> float:
        """Convert seconds to beat position."""
        if seconds <= 0:
            return 0.0

        total_beats = 0.0
        prev_beat = 0.0
        prev_bpm = self._changes[0][1]
        elapsed_seconds = 0.0

        for change_beat, change_bpm in self._changes[1:]:
            segment_beats = change_beat - prev_beat
            segment_seconds = segment_beats * (60.0 / prev_bpm)

            if elapsed_seconds + segment_seconds >= seconds:
                break

            elapsed_seconds += segment_seconds
            total_beats = change_beat
            prev_beat = change_beat
            prev_bpm = change_bpm

        remaining_seconds = seconds - elapsed_seconds
        total_beats += remaining_seconds * (prev_bpm / 60.0)
        return total_beats


@dataclass
class BPMTimeline(Generic[Ctx, Target, Delta]):
    """Timeline that schedules clips at beat positions."""

    compose_fn: ComposeFn[Delta]
    tempo_map: TempoMap = field(default_factory=TempoMap)
    events: list[tuple[float, Clip[Ctx, Target, Delta]]] = field(default_factory=list)

    @property
    def duration(self) -> float | None:
        """Total duration in seconds."""
        if not self.events:
            return 0.0
        max_end: float = 0.0
        for start_beat, clip in self.events:
            clip_dur = clip.duration
            if clip_dur is None:
                return None
            start_seconds = self.tempo_map.time(start_beat)
            max_end = max(max_end, start_seconds + clip_dur)
        return max_end

    def add(
        self, beat: float, clip: Clip[Ctx, Target, Delta]
    ) -> BPMTimeline[Ctx, Target, Delta]:
        """Add clip at beat position."""
        self.events.append((beat, clip))
        return self

    def render(self, t: float, ctx: Ctx) -> dict[Target, Delta]:
        """Render at time t (seconds)."""
        target_deltas: dict[Target, list[Delta]] = {}

        for start_beat, clip in self.events:
            start_seconds = self.tempo_map.time(start_beat)
            local_t = t - start_seconds
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
