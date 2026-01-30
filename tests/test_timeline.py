"""Tests for generic timeline library."""

from dataclasses import dataclass

import pytest

from timeline import Clip, Timeline, Runner


@dataclass
class MockDelta:
    value: float = 0.0


@dataclass
class MockClip:
    clip_duration: float | None = 1.0
    output_value: float = 1.0

    @property
    def duration(self) -> float | None:
        return self.clip_duration

    def render(self, t: float, ctx: str) -> dict[str, MockDelta]:
        if t < 0 or (self.clip_duration is not None and t > self.clip_duration):
            return {}
        return {"target": MockDelta(value=self.output_value)}


def compose_deltas(deltas: list[MockDelta]) -> MockDelta:
    return MockDelta(value=sum(d.value for d in deltas))


class TestTimeline:
    """Timeline duration, rendering, and compositing."""

    def test_duration(self) -> None:
        timeline: Timeline[str, str, MockDelta] = Timeline(compose_fn=compose_deltas)
        assert timeline.duration == 0.0

        timeline.add(1.0, MockClip(clip_duration=5.0))
        assert timeline.duration == 6.0

    def test_infinite_duration(self) -> None:
        timeline: Timeline[str, str, MockDelta] = Timeline(compose_fn=compose_deltas)
        timeline.add(0.0, MockClip(clip_duration=None))
        assert timeline.duration is None

    def test_add_chains(self) -> None:
        timeline: Timeline[str, str, MockDelta] = Timeline(compose_fn=compose_deltas)
        result = timeline.add(0.0, MockClip())
        assert result is timeline

    def test_render_timing(self) -> None:
        timeline: Timeline[str, str, MockDelta] = Timeline(compose_fn=compose_deltas)
        timeline.add(1.0, MockClip(clip_duration=2.0))

        assert timeline.render(0.5, "ctx") == {}  # before
        assert "target" in timeline.render(1.5, "ctx")  # during
        assert timeline.render(4.0, "ctx") == {}  # after

    def test_time_adjustment(self) -> None:
        """Clip receives time relative to its start."""
        @dataclass
        class TimeRecordingClip:
            clip_duration: float | None = 2.0
            received_t: float | None = None

            @property
            def duration(self) -> float | None:
                return self.clip_duration

            def render(self, t: float, ctx: str) -> dict[str, MockDelta]:
                self.received_t = t
                return {"target": MockDelta(value=t)}

        clip = TimeRecordingClip()
        timeline: Timeline[str, str, MockDelta] = Timeline(compose_fn=compose_deltas)
        timeline.add(5.0, clip)
        timeline.render(6.5, "ctx")
        assert clip.received_t == 1.5

    def test_compositing(self) -> None:
        timeline: Timeline[str, str, MockDelta] = Timeline(compose_fn=compose_deltas)
        timeline.add(0.0, MockClip(clip_duration=2.0, output_value=0.3))
        timeline.add(0.0, MockClip(clip_duration=2.0, output_value=0.5))
        result = timeline.render(1.0, "ctx")
        assert result["target"].value == pytest.approx(0.8)


class TestRunner:
    """Runner.render_frame applies deltas."""

    def test_render_frame(self) -> None:
        applied: list[dict] = []

        def apply_fn(deltas: dict[str, MockDelta]) -> str:
            applied.append(deltas)
            return "output"

        runner: Runner[str, str, MockDelta, str] = Runner(ctx="context", apply_fn=apply_fn)
        result = runner.render_frame(MockClip(output_value=0.75), t=0.5)

        assert result == "output"
        assert applied[0]["target"].value == 0.75


class TestClipProtocol:
    """Clip protocol compliance."""

    def test_timeline_is_clip(self) -> None:
        """Timeline can be nested (satisfies Clip protocol)."""
        timeline: Timeline[str, str, MockDelta] = Timeline(compose_fn=compose_deltas)
        assert isinstance(timeline, Clip)
