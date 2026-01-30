"""Tests for clips and timeline."""

import pytest

from dmxld.attributes import DimmerAttr, RGBAttr
from dmxld.blend import BlendOp
from dmxld.clips import DimmerPulseClip, SceneClip, TimelineClip
from dmxld.model import Fixture, FixtureState, FixtureType, Rig, Vec3


MockFixtureType = FixtureType(DimmerAttr())


@pytest.fixture
def rig() -> Rig:
    fixture = Fixture(MockFixtureType, universe=1, address=1)
    return Rig([fixture])


class TestSceneClip:
    """SceneClip rendering and fades."""

    def test_renders_during_duration(self, rig: Rig) -> None:
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            clip_duration=10.0,
        )
        assert scene.duration == 10.0
        deltas = scene.render(5.0, rig)
        assert len(deltas) == 1

    def test_empty_outside_duration(self, rig: Rig) -> None:
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            clip_duration=5.0,
        )
        deltas = scene.render(10.0, rig)
        assert len(deltas) == 0

    def test_fade_in(self, rig: Rig) -> None:
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_in=2.0,
            clip_duration=10.0,
        )
        deltas = scene.render(1.0, rig)  # Halfway through fade_in
        delta = deltas[rig.all[0]]
        assert delta.get("dimmer")[1] == pytest.approx(0.5)

    def test_fade_out(self, rig: Rig) -> None:
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_out=2.0,
            clip_duration=10.0,
        )
        deltas = scene.render(9.0, rig)  # Halfway through fade_out
        delta = deltas[rig.all[0]]
        assert delta.get("dimmer")[1] == pytest.approx(0.5)

    def test_object_forms(self, rig: Rig) -> None:
        """Accepts fixtures list and FixtureState directly (not just callables)."""
        scene = SceneClip(
            selector=rig.all,
            params_fn=FixtureState(dimmer=0.8),
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, rig)
        delta = deltas[rig.all[0]]
        assert delta.get("dimmer")[1] == pytest.approx(0.8)


class TestDimmerPulseClip:
    """DimmerPulseClip produces MUL operations."""

    def test_produces_mul_delta(self, rig: Rig) -> None:
        pulse = DimmerPulseClip(
            selector=lambda r: r.all,
            rate_hz=1.0,
            depth=0.5,
            base=0.5,
            clip_duration=5.0,
        )
        deltas = pulse.render(0.0, rig)
        delta = deltas[rig.all[0]]
        assert delta.get("dimmer")[0] == BlendOp.MUL


class TestTimelineClip:
    """TimelineClip scheduling and compositing."""

    def test_duration_from_children(self) -> None:
        timeline = TimelineClip()
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            clip_duration=5.0,
        )
        timeline.add(10.0, scene)
        assert timeline.duration == 15.0  # 10.0 + 5.0

    def test_add_chains(self) -> None:
        timeline = TimelineClip()
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            clip_duration=5.0,
        )
        result = timeline.add(0.0, scene)
        assert result is timeline

    def test_time_adjustment(self, rig: Rig) -> None:
        """Child clip receives time relative to its start."""
        timeline = TimelineClip()
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            clip_duration=5.0,
        )
        timeline.add(2.0, scene)

        # Before scene starts
        assert len(timeline.render(1.0, rig)) == 0
        # During scene
        assert len(timeline.render(3.0, rig)) == 1
        # After scene ends
        assert len(timeline.render(8.0, rig)) == 0

    def test_overlapping_clips(self, rig: Rig) -> None:
        """Both clips contribute when overlapping."""
        timeline = TimelineClip()
        scene1 = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=0.5),
            clip_duration=10.0,
        )
        scene2 = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=0.8),
            clip_duration=10.0,
        )
        timeline.add(0.0, scene1)
        timeline.add(5.0, scene2)

        # At t=7.0, both clips are active
        deltas = timeline.render(7.0, rig)
        assert rig.all[0] in deltas
