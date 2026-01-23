"""Unit tests for clips."""

import pytest

from fcld.blend import BlendOp
from fcld.clips import DimmerPulseClip, SceneClip, TimelineClip
from fcld.model import Fixture, FixtureState, FixtureType, Rig, Vec3


class MockFixtureType(FixtureType):
    """Simple fixture type for testing."""

    channel_count = 4

    @property
    def name(self) -> str:
        return "Mock"

    def encode(self, state: FixtureState) -> dict[int, int]:
        return {0: int(state.dimmer * 255)}


@pytest.fixture
def simple_rig() -> Rig:
    """Create a simple rig with one fixture."""
    fixture = Fixture(
        fixture_type=MockFixtureType(),
        universe=1,
        address=1,
        pos=Vec3(0, 0, 0),
        tags=set(),
    )
    return Rig([fixture])


class TestSceneClip:
    """Tests for SceneClip."""

    def test_duration(self) -> None:
        """Duration is set from clip_duration."""
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_in=1.0,
            fade_out=1.0,
            clip_duration=10.0,
        )
        assert scene.duration == 10.0

    def test_render_full_intensity(self, simple_rig: Rig) -> None:
        """Renders at full intensity during body."""
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.5, 0.0)),
            fade_in=1.0,
            fade_out=1.0,
            clip_duration=10.0,
        )
        deltas = scene.render(5.0, simple_rig)
        fixture = simple_rig.all[0]
        assert fixture in deltas
        delta = deltas[fixture]
        assert delta.dimmer is not None
        assert delta.dimmer[1] == pytest.approx(1.0)

    def test_render_fade_in(self, simple_rig: Rig) -> None:
        """Renders faded during fade_in period."""
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_in=2.0,
            fade_out=0.0,
            clip_duration=10.0,
        )
        deltas = scene.render(1.0, simple_rig)  # Halfway through fade_in
        fixture = simple_rig.all[0]
        delta = deltas[fixture]
        assert delta.dimmer is not None
        assert delta.dimmer[1] == pytest.approx(0.5)

    def test_render_fade_out(self, simple_rig: Rig) -> None:
        """Renders faded during fade_out period."""
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_in=0.0,
            fade_out=2.0,
            clip_duration=10.0,
        )
        deltas = scene.render(9.0, simple_rig)  # Halfway through fade_out
        fixture = simple_rig.all[0]
        delta = deltas[fixture]
        assert delta.dimmer is not None
        assert delta.dimmer[1] == pytest.approx(0.5)

    def test_render_outside_duration_empty(self, simple_rig: Rig) -> None:
        """Returns empty deltas outside clip duration."""
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=5.0,
        )
        deltas = scene.render(10.0, simple_rig)
        assert len(deltas) == 0

    def test_object_selector(self, simple_rig: Rig) -> None:
        """Accepts a list of fixtures as selector."""
        fixtures = simple_rig.all
        scene = SceneClip(
            selector=fixtures,  # List instead of callable
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, simple_rig)
        assert len(deltas) == 1

    def test_object_params_fn(self, simple_rig: Rig) -> None:
        """Accepts a FixtureState as params_fn."""
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=FixtureState(dimmer=0.8, rgb=(1.0, 0.0, 0.0)),  # Object instead of callable
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, simple_rig)
        fixture = simple_rig.all[0]
        delta = deltas[fixture]
        assert delta.dimmer is not None
        assert delta.dimmer[1] == pytest.approx(0.8)

    def test_both_object_forms(self, simple_rig: Rig) -> None:
        """Accepts both selector and params_fn as objects."""
        fixtures = simple_rig.all
        scene = SceneClip(
            selector=fixtures,
            params_fn=FixtureState(dimmer=0.5),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, simple_rig)
        fixture = simple_rig.all[0]
        delta = deltas[fixture]
        assert delta.dimmer is not None
        assert delta.dimmer[1] == pytest.approx(0.5)


class TestDimmerPulseClip:
    """Tests for DimmerPulseClip."""

    def test_duration(self) -> None:
        """Duration is set from clip_duration."""
        pulse = DimmerPulseClip(
            selector=lambda r: r.all,
            rate_hz=1.0,
            depth=0.5,
            base=0.5,
            clip_duration=5.0,
        )
        assert pulse.duration == 5.0

    def test_render_produces_mul_delta(self, simple_rig: Rig) -> None:
        """Pulse produces MUL blend operation."""
        pulse = DimmerPulseClip(
            selector=lambda r: r.all,
            rate_hz=1.0,
            depth=0.5,
            base=0.5,
            clip_duration=5.0,
        )
        deltas = pulse.render(0.0, simple_rig)
        fixture = simple_rig.all[0]
        assert fixture in deltas
        delta = deltas[fixture]
        assert delta.dimmer is not None
        assert delta.dimmer[0] == BlendOp.MUL

    def test_render_outside_duration_empty(self, simple_rig: Rig) -> None:
        """Returns empty deltas outside clip duration."""
        pulse = DimmerPulseClip(
            selector=lambda r: r.all,
            rate_hz=1.0,
            depth=0.5,
            base=0.5,
            clip_duration=5.0,
        )
        deltas = pulse.render(10.0, simple_rig)
        assert len(deltas) == 0

    def test_object_selector(self, simple_rig: Rig) -> None:
        """Accepts a list of fixtures as selector."""
        fixtures = simple_rig.all
        pulse = DimmerPulseClip(
            selector=fixtures,  # List instead of callable
            rate_hz=1.0,
            depth=0.5,
            base=0.5,
            clip_duration=5.0,
        )
        deltas = pulse.render(0.0, simple_rig)
        assert len(deltas) == 1


class TestTimelineClip:
    """Tests for TimelineClip."""

    def test_empty_timeline_duration_zero(self) -> None:
        """Empty timeline has duration 0."""
        timeline = TimelineClip()
        assert timeline.duration == 0.0

    def test_add_returns_self(self) -> None:
        """Add returns self for chaining."""
        timeline = TimelineClip()
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=5.0,
        )
        result = timeline.add(0.0, scene)
        assert result is timeline

    def test_duration_from_child_clips(self) -> None:
        """Duration calculated from child clips."""
        timeline = TimelineClip()
        scene1 = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=5.0,
        )
        scene2 = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=3.0,
        )
        timeline.add(0.0, scene1)  # ends at 5.0
        timeline.add(10.0, scene2)  # ends at 13.0
        assert timeline.duration == 13.0

    def test_render_empty_timeline(self, simple_rig: Rig) -> None:
        """Empty timeline renders empty deltas."""
        timeline = TimelineClip()
        deltas = timeline.render(0.0, simple_rig)
        assert len(deltas) == 0

    def test_render_passes_adjusted_time(self, simple_rig: Rig) -> None:
        """Render passes time adjusted for start offset."""
        timeline = TimelineClip()
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=5.0,
        )
        timeline.add(2.0, scene)

        # At t=1.0, scene hasn't started yet
        deltas_before = timeline.render(1.0, simple_rig)
        assert len(deltas_before) == 0

        # At t=3.0, scene is active (local time = 1.0)
        deltas_during = timeline.render(3.0, simple_rig)
        assert len(deltas_during) == 1

        # At t=8.0, scene has ended
        deltas_after = timeline.render(8.0, simple_rig)
        assert len(deltas_after) == 0


class TestTimelineClipCompositing:
    """Tests for timeline clip compositing."""

    def test_overlapping_clips_both_render(self, simple_rig: Rig) -> None:
        """Overlapping clips both contribute to output."""
        timeline = TimelineClip()
        scene1 = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=0.5),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=10.0,
        )
        scene2 = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=0.8),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=10.0,
        )
        timeline.add(0.0, scene1)
        timeline.add(5.0, scene2)

        # At t=7.0, both clips are active
        deltas = timeline.render(7.0, simple_rig)
        fixture = simple_rig.all[0]
        # Should have deltas from both clips merged
        assert fixture in deltas
