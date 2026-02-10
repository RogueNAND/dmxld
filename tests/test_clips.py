"""Tests for clips."""

import pytest

from dmxld.attributes import DimmerAttr, RGBAttr, RGBWAttr
from dmxld.blend import BlendOp
from dmxld.clips import EffectClip, SceneClip
from dmxld.model import Fixture, FixtureState, FixtureType, Rig, Vec3


DimmerOnly = FixtureType(DimmerAttr())
RGBDimmer = FixtureType(DimmerAttr(), RGBAttr())


@pytest.fixture
def rig() -> Rig:
    return Rig([Fixture(DimmerOnly, universe=1, address=1)])


@pytest.fixture
def multi_rig() -> Rig:
    """Rig with multiple fixtures at different positions."""
    return Rig([
        Fixture(RGBDimmer, universe=1, address=1, pos=Vec3(0.0, 0.0, 0.0)),
        Fixture(RGBDimmer, universe=1, address=5, pos=Vec3(1.0, 0.0, 0.0)),
        Fixture(RGBDimmer, universe=1, address=9, pos=Vec3(2.0, 0.0, 0.0)),
    ])


class TestSceneClip:
    def test_render(self, rig: Rig) -> None:
        scene = SceneClip(
            selector=lambda r: r.all,
            params=lambda f: FixtureState(dimmer=1.0),
            clip_duration=10.0,
        )
        assert scene.duration == 10.0
        assert len(scene.render(5.0, rig)) == 1
        assert len(scene.render(15.0, rig)) == 0  # outside duration

    def test_fade_in_out(self, rig: Rig) -> None:
        scene = SceneClip(
            selector=lambda r: r.all,
            params=lambda f: FixtureState(dimmer=1.0),
            fade_in=2.0,
            fade_out=2.0,
            clip_duration=10.0,
        )
        # Halfway through fade_in
        delta = scene.render(1.0, rig)[rig.all[0]]
        assert delta["dimmer"][1] == pytest.approx(0.5)

        # Halfway through fade_out
        delta = scene.render(9.0, rig)[rig.all[0]]
        assert delta["dimmer"][1] == pytest.approx(0.5)

    def test_object_forms(self, rig: Rig) -> None:
        """Accepts fixtures list and FixtureState directly."""
        scene = SceneClip(
            selector=rig.all,
            params=FixtureState(dimmer=0.8),
            clip_duration=5.0,
        )
        delta = scene.render(1.0, rig)[rig.all[0]]
        assert delta["dimmer"][1] == pytest.approx(0.8)

    def test_blend_op(self, rig: Rig) -> None:
        scene_set = SceneClip(
            selector=lambda r: r.all,
            params=lambda f: FixtureState(dimmer=0.5),
            clip_duration=5.0,
        )
        scene_mul = SceneClip(
            selector=lambda r: r.all,
            params=lambda f: FixtureState(dimmer=0.5),
            clip_duration=5.0,
            blend_op=BlendOp.MUL,
        )
        assert scene_set.render(1.0, rig)[rig.all[0]]["dimmer"][0] == BlendOp.SET
        assert scene_mul.render(1.0, rig)[rig.all[0]]["dimmer"][0] == BlendOp.MUL


class TestSceneClipLayers:
    """SceneClip with multi-layer support."""

    @pytest.fixture
    def two_group_rig(self) -> Rig:
        from dmxld.model import FixtureGroup
        self.front = FixtureGroup()
        self.back = FixtureGroup()
        FrontType = FixtureType(DimmerAttr(), RGBAttr(), groups={self.front})
        BackType = FixtureType(DimmerAttr(), RGBAttr(), groups={self.back})
        return Rig([
            FrontType(universe=1, address=1),
            FrontType(universe=1, address=5),
            BackType(universe=1, address=9),
        ])

    def test_basic_layers(self, two_group_rig: Rig) -> None:
        """Layers apply different params to different selectors."""
        scene = SceneClip(
            layers=[
                (self.front, FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))),
                (self.back, FixtureState(dimmer=0.5, color=(0.0, 0.0, 1.0))),
            ],
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, two_group_rig)
        assert len(deltas) == 3

        # Front fixtures get red
        front_fixtures = list(self.front)
        for f in front_fixtures:
            assert deltas[f]["dimmer"][1] == pytest.approx(1.0)
            assert deltas[f]["color"][1] == (1.0, 0.0, 0.0)

        # Back fixture gets blue
        back_fixtures = list(self.back)
        for f in back_fixtures:
            assert deltas[f]["dimmer"][1] == pytest.approx(0.5)
            assert deltas[f]["color"][1] == (0.0, 0.0, 1.0)

    def test_later_layer_overwrites(self, two_group_rig: Rig) -> None:
        """Later layers overwrite earlier ones for the same fixture."""
        all_fixtures = two_group_rig.all
        scene = SceneClip(
            layers=[
                (lambda r: r.all, FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))),
                (self.front, FixtureState(dimmer=0.5, color=(0.0, 1.0, 0.0))),
            ],
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, two_group_rig)

        # Front fixtures overwritten by second layer
        for f in self.front:
            assert deltas[f]["dimmer"][1] == pytest.approx(0.5)
            assert deltas[f]["color"][1] == (0.0, 1.0, 0.0)

        # Back fixture keeps first layer
        back_fixtures = [f for f in all_fixtures if f not in list(self.front)]
        for f in back_fixtures:
            assert deltas[f]["dimmer"][1] == pytest.approx(1.0)
            assert deltas[f]["color"][1] == (1.0, 0.0, 0.0)

    def test_layers_with_callable_params(self, two_group_rig: Rig) -> None:
        """Layers accept callable params."""
        scene = SceneClip(
            layers=[
                (self.front, lambda f: FixtureState(dimmer=0.8)),
                (self.back, lambda f: FixtureState(dimmer=0.3)),
            ],
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, two_group_rig)
        for f in self.front:
            assert deltas[f]["dimmer"][1] == pytest.approx(0.8)
        for f in self.back:
            assert deltas[f]["dimmer"][1] == pytest.approx(0.3)

    def test_layers_with_fade(self, two_group_rig: Rig) -> None:
        """Fade applies to all layers."""
        scene = SceneClip(
            layers=[
                (self.front, FixtureState(dimmer=1.0)),
                (self.back, FixtureState(dimmer=1.0)),
            ],
            fade_in=2.0,
            clip_duration=5.0,
        )
        deltas = scene.render(1.0, two_group_rig)
        for f in self.front:
            assert deltas[f]["dimmer"][1] == pytest.approx(0.5)
        for f in self.back:
            assert deltas[f]["dimmer"][1] == pytest.approx(0.5)

    def test_mutual_exclusivity(self) -> None:
        """Cannot use both selector/params and layers."""
        with pytest.raises(ValueError, match="not both"):
            SceneClip(
                selector=lambda r: r.all,
                params=FixtureState(dimmer=1.0),
                layers=[(lambda r: r.all, FixtureState(dimmer=1.0))],
                clip_duration=5.0,
            )

    def test_missing_both(self) -> None:
        """Must provide either selector/params or layers."""
        with pytest.raises(ValueError, match="Provide"):
            SceneClip(clip_duration=5.0)

    def test_partial_single_form(self) -> None:
        """Must provide both selector and params in single-layer form."""
        with pytest.raises(ValueError, match="Both selector and params"):
            SceneClip(selector=lambda r: r.all, clip_duration=5.0)


class TestEffectClip:
    def test_params_signature(self, multi_rig: Rig) -> None:
        """params receives (t, fixture, index, segment)."""
        calls: list[tuple] = []

        def capture(t: float, f: Fixture, i: int, seg: int) -> FixtureState:
            calls.append((t, f.pos.x, i, seg))
            return FixtureState(dimmer=1.0)

        effect = EffectClip(
            selector=lambda r: r.all,
            params=capture,
            clip_duration=10.0,
        )
        effect.render(5.0, multi_rig)

        assert len(calls) == 3
        assert all(t == 5.0 for t, _, _, _ in calls)
        assert [i for _, _, i, _ in calls] == [0, 1, 2]
        assert all(seg == 0 for _, _, _, seg in calls)

    def test_fixture_position_access(self, multi_rig: Rig) -> None:
        """Can use fixture position in params."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(dimmer=f.pos.x / 2.0),
            clip_duration=10.0,
        )
        deltas = effect.render(0.0, multi_rig)
        fixtures = multi_rig.all
        assert deltas[fixtures[0]]["dimmer"][1] == pytest.approx(0.0)
        assert deltas[fixtures[1]]["dimmer"][1] == pytest.approx(0.5)
        assert deltas[fixtures[2]]["dimmer"][1] == pytest.approx(1.0)

    def test_fade_in_out(self, multi_rig: Rig) -> None:
        effect = EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(dimmer=1.0),
            fade_in=2.0,
            fade_out=2.0,
            clip_duration=10.0,
        )
        # All fixtures should have same fade
        for fixture in multi_rig.all:
            assert effect.render(1.0, multi_rig)[fixture]["dimmer"][1] == pytest.approx(0.5)
            assert effect.render(9.0, multi_rig)[fixture]["dimmer"][1] == pytest.approx(0.5)

    def test_empty_outside_duration(self, multi_rig: Rig) -> None:
        effect = EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(dimmer=1.0),
            clip_duration=5.0,
        )
        assert len(effect.render(-1.0, multi_rig)) == 0
        assert len(effect.render(10.0, multi_rig)) == 0


class TestSegmentedEffectClip:
    """EffectClip with segmented fixtures."""

    @pytest.fixture
    def segmented_rig(self) -> Rig:
        LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=4))
        return Rig([Fixture(LEDBar, universe=1, address=1)])

    def test_params_called_per_segment(self, segmented_rig: Rig) -> None:
        segments: list[int] = []

        def capture(t: float, f: Fixture, i: int, seg: int) -> FixtureState:
            segments.append(seg)
            return FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))

        effect = EffectClip(
            selector=lambda r: r.all,
            params=capture,
            clip_duration=10.0,
        )
        effect.render(0.0, segmented_rig)

        assert segments == [0, 1, 2, 3]

    def test_per_segment_colors(self, segmented_rig: Rig) -> None:
        colors = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 1.0, 0.0)]

        effect = EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(dimmer=1.0, color=colors[seg]),
            clip_duration=10.0,
        )
        delta = effect.render(0.0, segmented_rig)[segmented_rig.all[0]]

        for seg, color in enumerate(colors):
            assert delta[f"color_{seg}"][1] == color

    def test_dimmer_set_once(self, segmented_rig: Rig) -> None:
        """Dimmer is fixture-level, only set on first segment."""
        effect = EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(dimmer=0.5, color=(1.0, 0.0, 0.0)),
            clip_duration=10.0,
        )
        delta = effect.render(0.0, segmented_rig)[segmented_rig.all[0]]
        assert delta["dimmer"][1] == pytest.approx(0.5)
