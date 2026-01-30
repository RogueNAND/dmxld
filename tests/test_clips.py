"""Tests for clips and timeline."""

import pytest

from dmxld.attributes import DimmerAttr, RGBAttr
from dmxld.blend import BlendOp
from dmxld.clips import EffectClip, SceneClip, TimelineClip
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

    def test_blend_op_default_is_set(self, rig: Rig) -> None:
        """Default blend_op is SET."""
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=0.5),
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, rig)
        delta = deltas[rig.all[0]]
        assert delta.get("dimmer")[0] == BlendOp.SET

    def test_blend_op_mul(self, rig: Rig) -> None:
        """Can specify MUL blend_op."""
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=0.5),
            clip_duration=5.0,
            blend_op=BlendOp.MUL,
        )
        deltas = scene.render(1.0, rig)
        delta = deltas[rig.all[0]]
        assert delta.get("dimmer")[0] == BlendOp.MUL


@pytest.fixture
def multi_fixture_rig() -> Rig:
    """Rig with multiple fixtures at different positions."""
    fixture_type = FixtureType(DimmerAttr(), RGBAttr())
    return Rig([
        Fixture(fixture_type, universe=1, address=1, pos=Vec3(0.0, 0.0, 0.0)),
        Fixture(fixture_type, universe=1, address=5, pos=Vec3(1.0, 0.0, 0.0)),
        Fixture(fixture_type, universe=1, address=9, pos=Vec3(2.0, 0.0, 0.0)),
    ])


class TestEffectClip:
    """EffectClip with time, fixture, and index access."""

    def test_params_fn_receives_time(self, multi_fixture_rig: Rig) -> None:
        """params_fn receives current time."""
        received_times: list[float] = []

        def capture_time(t: float, f: Fixture, i: int) -> FixtureState:
            received_times.append(t)
            return FixtureState(dimmer=t / 10.0)

        effect = EffectClip(
            selector=lambda r: r.all,
            params_fn=capture_time,
            clip_duration=10.0,
        )
        effect.render(5.0, multi_fixture_rig)
        assert all(t == 5.0 for t in received_times)

    def test_params_fn_receives_fixture(self, multi_fixture_rig: Rig) -> None:
        """params_fn receives fixture with position access."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params_fn=lambda t, f, i: FixtureState(dimmer=f.pos.x / 2.0),
            clip_duration=10.0,
        )
        deltas = effect.render(0.0, multi_fixture_rig)
        fixtures = multi_fixture_rig.all
        # Dimmer should reflect x position: 0.0, 0.5, 1.0
        assert deltas[fixtures[0]].get("dimmer")[1] == pytest.approx(0.0)
        assert deltas[fixtures[1]].get("dimmer")[1] == pytest.approx(0.5)
        assert deltas[fixtures[2]].get("dimmer")[1] == pytest.approx(1.0)

    def test_params_fn_receives_index(self, multi_fixture_rig: Rig) -> None:
        """params_fn receives fixture index."""
        received_indices: list[int] = []

        def capture_index(t: float, f: Fixture, i: int) -> FixtureState:
            received_indices.append(i)
            return FixtureState(dimmer=1.0)

        effect = EffectClip(
            selector=lambda r: r.all,
            params_fn=capture_index,
            clip_duration=10.0,
        )
        effect.render(0.0, multi_fixture_rig)
        assert received_indices == [0, 1, 2]

    def test_fade_in(self, multi_fixture_rig: Rig) -> None:
        """Fade in applies to dimmer."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params_fn=lambda t, f, i: FixtureState(dimmer=1.0),
            fade_in=2.0,
            clip_duration=10.0,
        )
        deltas = effect.render(1.0, multi_fixture_rig)  # Halfway through fade_in
        for fixture in multi_fixture_rig.all:
            assert deltas[fixture].get("dimmer")[1] == pytest.approx(0.5)

    def test_fade_out(self, multi_fixture_rig: Rig) -> None:
        """Fade out applies to dimmer."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params_fn=lambda t, f, i: FixtureState(dimmer=1.0),
            fade_out=2.0,
            clip_duration=10.0,
        )
        deltas = effect.render(9.0, multi_fixture_rig)  # Halfway through fade_out
        for fixture in multi_fixture_rig.all:
            assert deltas[fixture].get("dimmer")[1] == pytest.approx(0.5)

    def test_empty_outside_duration(self, multi_fixture_rig: Rig) -> None:
        """Returns empty outside clip duration."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params_fn=lambda t, f, i: FixtureState(dimmer=1.0),
            clip_duration=5.0,
        )
        assert len(effect.render(-1.0, multi_fixture_rig)) == 0
        assert len(effect.render(10.0, multi_fixture_rig)) == 0

    def test_blend_op_default_is_set(self, multi_fixture_rig: Rig) -> None:
        """Default blend_op is SET."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params_fn=lambda t, f, i: FixtureState(dimmer=0.5),
            clip_duration=5.0,
        )
        deltas = effect.render(1.0, multi_fixture_rig)
        delta = deltas[multi_fixture_rig.all[0]]
        assert delta.get("dimmer")[0] == BlendOp.SET

    def test_blend_op_mul(self, multi_fixture_rig: Rig) -> None:
        """Can specify MUL blend_op for layered effects."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params_fn=lambda t, f, i: FixtureState(dimmer=0.5),
            clip_duration=5.0,
            blend_op=BlendOp.MUL,
        )
        deltas = effect.render(1.0, multi_fixture_rig)
        delta = deltas[multi_fixture_rig.all[0]]
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
