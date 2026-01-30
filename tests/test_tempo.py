"""Tests for TempoMap and BPMTimeline."""

from __future__ import annotations

import pytest

from timeline.tempo import TempoMap, BPMTimeline


class TestTempoMap:
    """Tests for TempoMap beat/time conversion."""

    def test_single_tempo_time(self) -> None:
        """Convert beats to seconds at constant tempo."""
        tempo = TempoMap(120)  # 120 BPM = 2 beats per second
        assert tempo.time(0) == 0.0
        assert tempo.time(2) == pytest.approx(1.0)
        assert tempo.time(4) == pytest.approx(2.0)

    def test_single_tempo_beat(self) -> None:
        """Convert seconds to beats at constant tempo."""
        tempo = TempoMap(120)
        assert tempo.beat(0) == 0.0
        assert tempo.beat(1.0) == pytest.approx(2.0)
        assert tempo.beat(2.0) == pytest.approx(4.0)

    def test_tempo_change_time(self) -> None:
        """Convert beats to seconds across tempo change."""
        tempo = TempoMap(120)
        tempo.set_tempo(4, 60)  # Change to 60 BPM at beat 4

        # First 4 beats at 120 BPM = 2 seconds
        assert tempo.time(4) == pytest.approx(2.0)
        # Next 4 beats at 60 BPM = 4 seconds more
        assert tempo.time(8) == pytest.approx(6.0)

    def test_tempo_change_beat(self) -> None:
        """Convert seconds to beats across tempo change."""
        tempo = TempoMap(120)
        tempo.set_tempo(4, 60)

        assert tempo.beat(2.0) == pytest.approx(4.0)  # End of first segment
        assert tempo.beat(6.0) == pytest.approx(8.0)  # After tempo change

    def test_multiple_tempo_changes(self) -> None:
        """Multiple tempo changes in sequence."""
        tempo = TempoMap(120)
        tempo.set_tempo(4, 60)   # Slow at beat 4
        tempo.set_tempo(8, 180)  # Fast at beat 8

        # 4 beats at 120 = 2s, 4 beats at 60 = 4s, total = 6s at beat 8
        assert tempo.time(8) == pytest.approx(6.0)
        # 2 beats at 180 BPM = 2/3 second more
        assert tempo.time(10) == pytest.approx(6.0 + 2/3)

    def test_set_tempo_chainable(self) -> None:
        """set_tempo returns self for chaining."""
        tempo = TempoMap(120).set_tempo(4, 60).set_tempo(8, 90)
        assert tempo.time(4) == pytest.approx(2.0)

    def test_set_tempo_at_zero(self) -> None:
        """Setting tempo at beat 0 replaces initial tempo."""
        tempo = TempoMap(120)
        tempo.set_tempo(0, 60)
        assert tempo.time(4) == pytest.approx(4.0)  # 4 beats at 60 BPM

    def test_negative_beats_returns_zero(self) -> None:
        """Negative beat values return 0."""
        tempo = TempoMap(120)
        assert tempo.time(-5) == 0.0
        assert tempo.beat(-5) == 0.0


class TestBPMTimeline:
    """Tests for BPMTimeline scheduling."""

    def test_add_at_beat(self) -> None:
        """Clip added at beat position renders at correct time."""
        from dataclasses import dataclass

        @dataclass
        class MockClip:
            duration: float = 1.0
            received_t: float | None = None

            def render(self, t: float, ctx: str) -> dict[str, str]:
                self.received_t = t
                return {"target": "delta"}

        def compose(deltas: list[str]) -> str:
            return deltas[0]

        tempo = TempoMap(120)
        timeline: BPMTimeline[str, str, str] = BPMTimeline(
            compose_fn=compose, tempo_map=tempo
        )

        clip = MockClip()
        timeline.add(4, clip)  # Add at beat 4 = 2 seconds

        # Before clip starts
        result = timeline.render(1.5, "ctx")
        assert result == {}
        assert clip.received_t is None

        # At clip start
        result = timeline.render(2.0, "ctx")
        assert result == {"target": "delta"}
        assert clip.received_t == pytest.approx(0.0)

        # Mid-clip
        result = timeline.render(2.5, "ctx")
        assert clip.received_t == pytest.approx(0.5)

    def test_duration_calculation(self) -> None:
        """Timeline duration accounts for tempo changes."""
        from dataclasses import dataclass

        @dataclass
        class MockClip:
            duration: float = 2.0

            def render(self, t: float, ctx: str) -> dict[str, str]:
                return {}

        def compose(deltas: list[str]) -> str:
            return ""

        tempo = TempoMap(120)
        tempo.set_tempo(4, 60)

        timeline: BPMTimeline[str, str, str] = BPMTimeline(
            compose_fn=compose, tempo_map=tempo
        )
        timeline.add(4, MockClip())  # Beat 4 = 2 seconds, duration 2 seconds

        # Duration = start_seconds (2.0) + clip_duration (2.0) = 4.0
        assert timeline.duration == pytest.approx(4.0)

    def test_add_chainable(self) -> None:
        """add() returns self for chaining."""
        from dataclasses import dataclass

        @dataclass
        class MockClip:
            duration: float = 1.0

            def render(self, t: float, ctx: str) -> dict[str, str]:
                return {}

        def compose(deltas: list[str]) -> str:
            return ""

        timeline: BPMTimeline[str, str, str] = BPMTimeline(compose_fn=compose)
        result = timeline.add(0, MockClip()).add(4, MockClip())
        assert result is timeline
        assert len(timeline.events) == 2
