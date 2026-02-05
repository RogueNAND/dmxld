"""Tests for clips."""

import pytest

from dmxld.attributes import DimmerAttr, RGBAttr
from dmxld.blend import BlendOp
from dmxld.clips import EffectClip, SceneClip
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
            params=lambda f: FixtureState(dimmer=1.0),
            clip_duration=10.0,
        )
        assert scene.duration == 10.0
        deltas = scene.render(5.0, rig)
        assert len(deltas) == 1

    def test_empty_outside_duration(self, rig: Rig) -> None:
        scene = SceneClip(
            selector=lambda r: r.all,
            params=lambda f: FixtureState(dimmer=1.0),
            clip_duration=5.0,
        )
        deltas = scene.render(10.0, rig)
        assert len(deltas) == 0

    def test_fade_in(self, rig: Rig) -> None:
        scene = SceneClip(
            selector=lambda r: r.all,
            params=lambda f: FixtureState(dimmer=1.0),
            fade_in=2.0,
            clip_duration=10.0,
        )
        deltas = scene.render(1.0, rig)  # Halfway through fade_in
        delta = deltas[rig.all[0]]
        assert delta.get("dimmer")[1] == pytest.approx(0.5)

    def test_fade_out(self, rig: Rig) -> None:
        scene = SceneClip(
            selector=lambda r: r.all,
            params=lambda f: FixtureState(dimmer=1.0),
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
            params=FixtureState(dimmer=0.8),
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, rig)
        delta = deltas[rig.all[0]]
        assert delta.get("dimmer")[1] == pytest.approx(0.8)

    def test_blend_op_default_is_set(self, rig: Rig) -> None:
        """Default blend_op is SET."""
        scene = SceneClip(
            selector=lambda r: r.all,
            params=lambda f: FixtureState(dimmer=0.5),
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, rig)
        delta = deltas[rig.all[0]]
        assert delta.get("dimmer")[0] == BlendOp.SET

    def test_blend_op_mul(self, rig: Rig) -> None:
        """Can specify MUL blend_op."""
        scene = SceneClip(
            selector=lambda r: r.all,
            params=lambda f: FixtureState(dimmer=0.5),
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
    """EffectClip with time, fixture, index, and segment access."""

    def test_params_receives_time(self, multi_fixture_rig: Rig) -> None:
        """params receives current time."""
        received_times: list[float] = []

        def capture_time(t: float, f: Fixture, i: int, seg: int) -> FixtureState:
            received_times.append(t)
            return FixtureState(dimmer=t / 10.0)

        effect = EffectClip(
            selector=lambda r: r.all,
            params=capture_time,
            clip_duration=10.0,
        )
        effect.render(5.0, multi_fixture_rig)
        assert all(t == 5.0 for t in received_times)

    def test_params_receives_fixture(self, multi_fixture_rig: Rig) -> None:
        """params receives fixture with position access."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(dimmer=f.pos.x / 2.0),
            clip_duration=10.0,
        )
        deltas = effect.render(0.0, multi_fixture_rig)
        fixtures = multi_fixture_rig.all
        # Dimmer should reflect x position: 0.0, 0.5, 1.0
        assert deltas[fixtures[0]].get("dimmer")[1] == pytest.approx(0.0)
        assert deltas[fixtures[1]].get("dimmer")[1] == pytest.approx(0.5)
        assert deltas[fixtures[2]].get("dimmer")[1] == pytest.approx(1.0)

    def test_params_receives_index(self, multi_fixture_rig: Rig) -> None:
        """params receives fixture index."""
        received_indices: list[int] = []

        def capture_index(t: float, f: Fixture, i: int, seg: int) -> FixtureState:
            received_indices.append(i)
            return FixtureState(dimmer=1.0)

        effect = EffectClip(
            selector=lambda r: r.all,
            params=capture_index,
            clip_duration=10.0,
        )
        effect.render(0.0, multi_fixture_rig)
        assert received_indices == [0, 1, 2]

    def test_params_receives_segment(self, multi_fixture_rig: Rig) -> None:
        """params receives segment index (0 for non-segmented fixtures)."""
        received_segments: list[int] = []

        def capture_segment(t: float, f: Fixture, i: int, seg: int) -> FixtureState:
            received_segments.append(seg)
            return FixtureState(dimmer=1.0)

        effect = EffectClip(
            selector=lambda r: r.all,
            params=capture_segment,
            clip_duration=10.0,
        )
        effect.render(0.0, multi_fixture_rig)
        # Non-segmented fixtures always have seg=0
        assert all(s == 0 for s in received_segments)

    def test_fade_in(self, multi_fixture_rig: Rig) -> None:
        """Fade in applies to dimmer."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(dimmer=1.0),
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
            params=lambda t, f, i, seg: FixtureState(dimmer=1.0),
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
            params=lambda t, f, i, seg: FixtureState(dimmer=1.0),
            clip_duration=5.0,
        )
        assert len(effect.render(-1.0, multi_fixture_rig)) == 0
        assert len(effect.render(10.0, multi_fixture_rig)) == 0

    def test_blend_op_default_is_set(self, multi_fixture_rig: Rig) -> None:
        """Default blend_op is SET."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(dimmer=0.5),
            clip_duration=5.0,
        )
        deltas = effect.render(1.0, multi_fixture_rig)
        delta = deltas[multi_fixture_rig.all[0]]
        assert delta.get("dimmer")[0] == BlendOp.SET

    def test_blend_op_mul(self, multi_fixture_rig: Rig) -> None:
        """Can specify MUL blend_op for layered effects."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(dimmer=0.5),
            clip_duration=5.0,
            blend_op=BlendOp.MUL,
        )
        deltas = effect.render(1.0, multi_fixture_rig)
        delta = deltas[multi_fixture_rig.all[0]]
        assert delta.get("dimmer")[0] == BlendOp.MUL


from dmxld.attributes import RGBWAttr


@pytest.fixture
def segmented_fixture_rig() -> Rig:
    """Rig with a multi-segment fixture (LED bar with 4 RGBW segments)."""
    fixture_type = FixtureType(DimmerAttr(), RGBWAttr(segments=4))
    return Rig([Fixture(fixture_type, universe=1, address=1)])


class TestSegmentedEffectClip:
    """EffectClip with segmented fixtures."""

    def test_segment_count_property(self, segmented_fixture_rig: Rig) -> None:
        """Fixture reports correct segment count."""
        fixture = segmented_fixture_rig.all[0]
        assert fixture.segment_count == 4

    def test_params_called_per_segment(self, segmented_fixture_rig: Rig) -> None:
        """params is called once per segment."""
        call_count = 0
        received_segments: list[int] = []

        def capture(t: float, f: Fixture, i: int, seg: int) -> FixtureState:
            nonlocal call_count
            call_count += 1
            received_segments.append(seg)
            return FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))

        effect = EffectClip(
            selector=lambda r: r.all,
            params=capture,
            clip_duration=10.0,
        )
        effect.render(0.0, segmented_fixture_rig)
        assert call_count == 4
        assert received_segments == [0, 1, 2, 3]

    def test_segment_colors_in_delta(self, segmented_fixture_rig: Rig) -> None:
        """Each segment gets its own color in the delta."""
        colors = [
            (1.0, 0.0, 0.0),  # red
            (0.0, 1.0, 0.0),  # green
            (0.0, 0.0, 1.0),  # blue
            (1.0, 1.0, 0.0),  # yellow
        ]

        def per_segment_color(t: float, f: Fixture, i: int, seg: int) -> FixtureState:
            return FixtureState(dimmer=1.0, color=colors[seg])

        effect = EffectClip(
            selector=lambda r: r.all,
            params=per_segment_color,
            clip_duration=10.0,
        )
        deltas = effect.render(0.0, segmented_fixture_rig)
        fixture = segmented_fixture_rig.all[0]
        delta = deltas[fixture]

        # Should have color_0, color_1, color_2, color_3 keys
        assert delta.get("color_0")[1] == colors[0]
        assert delta.get("color_1")[1] == colors[1]
        assert delta.get("color_2")[1] == colors[2]
        assert delta.get("color_3")[1] == colors[3]

    def test_dimmer_set_once(self, segmented_fixture_rig: Rig) -> None:
        """Dimmer is only set on first segment (fixture-level)."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(dimmer=0.5, color=(1.0, 0.0, 0.0)),
            clip_duration=10.0,
        )
        deltas = effect.render(0.0, segmented_fixture_rig)
        fixture = segmented_fixture_rig.all[0]
        delta = deltas[fixture]

        # Dimmer should be present (from first segment)
        assert delta.get("dimmer")[1] == pytest.approx(0.5)
