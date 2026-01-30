"""Tests for DMXEngine rendering."""

import pytest

from dmxld.attributes import DimmerAttr, RGBAttr
from dmxld.clips import SceneClip
from dmxld.engine import DMXEngine
from dmxld.model import Fixture, FixtureState, FixtureType, Rig


RGBFixture = FixtureType(DimmerAttr(), RGBAttr())


@pytest.fixture
def rig() -> Rig:
    return Rig([Fixture(RGBFixture, universe=1, address=1)])


@pytest.fixture
def two_fixture_rig() -> Rig:
    return Rig([
        Fixture(RGBFixture, universe=1, address=1, tags={"left"}),
        Fixture(RGBFixture, universe=1, address=10, tags={"right"}),
    ])


class TestRenderFrame:
    """render_frame produces correct DMX output."""

    def test_full_white(self, rig: Rig) -> None:
        engine = DMXEngine(rig=rig)
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 1.0, 1.0)),
            clip_duration=10.0,
        )
        result = engine.render_frame(scene, t=1.0)

        # Fixture at address 1: dimmer=ch1, rgb=ch2-4
        assert result[1][1] == 255  # dimmer
        assert result[1][2] == 255  # red
        assert result[1][3] == 255  # green
        assert result[1][4] == 255  # blue

    def test_half_dimmer(self, rig: Rig) -> None:
        engine = DMXEngine(rig=rig)
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=0.5),
            clip_duration=10.0,
        )
        result = engine.render_frame(scene, t=1.0)
        assert result[1][1] == 127

    def test_multiple_fixtures(self, two_fixture_rig: Rig) -> None:
        engine = DMXEngine(rig=two_fixture_rig)
        scene = SceneClip(
            selector=lambda r: r.all,
            params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0)),
            clip_duration=10.0,
        )
        result = engine.render_frame(scene, t=1.0)

        # Fixture 1 at address 1
        assert result[1][1] == 255  # dimmer
        assert result[1][2] == 255  # red

        # Fixture 2 at address 10
        assert result[1][10] == 255  # dimmer
        assert result[1][11] == 255  # red

    def test_selector_filtering(self, two_fixture_rig: Rig) -> None:
        engine = DMXEngine(rig=two_fixture_rig)
        scene = SceneClip(
            selector=lambda r: r.by_tag("left"),
            params_fn=lambda f: FixtureState(dimmer=1.0),
            clip_duration=10.0,
        )
        result = engine.render_frame(scene, t=1.0)

        assert result[1][1] == 255   # left fixture lit
        assert result[1][10] == 0    # right fixture dark


class TestEngineLifecycle:
    """Engine initialization and stop."""

    def test_stop_without_play(self, rig: Rig) -> None:
        """Stop is safe to call before play."""
        engine = DMXEngine(rig=rig)
        engine.stop()  # Should not raise

    def test_optional_rig(self) -> None:
        """Engine can be created without rig, then set later."""
        engine = DMXEngine()
        assert engine.rig is None

        rig = Rig([Fixture(RGBFixture, 1, 1)])
        engine.set_rig(rig)
        assert engine.rig is rig
