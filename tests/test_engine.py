"""Unit tests for DMX engine."""

import pytest

from olald.blend import BlendOp, FixtureDelta
from olald.clips import SceneClip, TimelineClip
from olald.engine import DMXEngine
from olald.model import Fixture, FixtureContext, FixtureState, FixtureType, Rig, Vec3


class MockFixtureType(FixtureType):
    """Simple fixture type for testing (matches GenericRGBDimmer offsets)."""

    channel_count = 4

    @property
    def name(self) -> str:
        return "Mock"

    def encode(self, state: FixtureState) -> dict[int, int]:
        # Channel offsets: 0=dimmer, 1=R, 2=G, 3=B (same as GenericRGBDimmer)
        return {
            0: int(state.dimmer * 255),
            1: int(state.rgb[0] * 255),
            2: int(state.rgb[1] * 255),
            3: int(state.rgb[2] * 255),
        }


@pytest.fixture
def simple_rig() -> Rig:
    """Create a simple rig with one fixture."""
    fixture = Fixture(
        fixture_type=MockFixtureType(),
        universe=1,
        address=1,
        pos=Vec3(0, 0, 0),
        tags={"test"},
    )
    return Rig([fixture])


@pytest.fixture
def two_fixture_rig() -> Rig:
    """Create a rig with two fixtures."""
    f1 = Fixture(
        fixture_type=MockFixtureType(),
        universe=1,
        address=1,
        pos=Vec3(-1, 0, 0),
        tags={"left"},
    )
    f2 = Fixture(
        fixture_type=MockFixtureType(),
        universe=1,
        address=10,
        pos=Vec3(1, 0, 0),
        tags={"right"},
    )
    return Rig([f1, f2])


class TestDMXEngineRenderFrame:
    """Tests for render_frame without OLA."""

    def test_render_empty_clip(self, simple_rig: Rig) -> None:
        """Empty clip renders fixture states (initialized to zero)."""
        engine = DMXEngine(rig=simple_rig)
        timeline = TimelineClip()
        result = engine.render_frame(timeline, t=0.0)
        # Fixture at address 1, MockFixtureType encodes dimmer at offset 0 -> channel 1
        # Empty timeline produces no deltas, fixture state remains at initialized 0
        assert result[1][1] == 0  # dimmer at address 1 + offset 0

    def test_render_scene_full_white(self, simple_rig: Rig) -> None:
        """Full white scene renders 255 on all channels."""
        engine = DMXEngine(rig=simple_rig)
        scene = SceneClip(
            selector=lambda rig: rig.all,
            params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 1.0, 1.0)),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=10.0,
        )
        timeline = TimelineClip().add(0.0, scene)
        result = engine.render_frame(timeline, t=1.0)
        # MockFixtureType only encodes dimmer at offset 0
        # Fixture at address 1 -> channel 1
        assert result[1][1] == 255  # dimmer
        assert result[1][2] == 255  # red
        assert result[1][3] == 255  # green
        assert result[1][4] == 255  # blue

    def test_render_scene_half_dimmer(self, simple_rig: Rig) -> None:
        """Half dimmer renders 127."""
        engine = DMXEngine(rig=simple_rig)
        scene = SceneClip(
            selector=lambda rig: rig.all,
            params_fn=lambda f: FixtureState(dimmer=0.5, rgb=(1.0, 1.0, 1.0)),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=10.0,
        )
        timeline = TimelineClip().add(0.0, scene)
        result = engine.render_frame(timeline, t=1.0)
        assert result[1][1] == 127  # dimmer (0.5 * 255 = 127.5, truncated)

    def test_render_two_fixtures_different_addresses(self, two_fixture_rig: Rig) -> None:
        """Two fixtures render to correct addresses."""
        engine = DMXEngine(rig=two_fixture_rig)
        scene = SceneClip(
            selector=lambda rig: rig.all,
            params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0)),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=10.0,
        )
        timeline = TimelineClip().add(0.0, scene)
        result = engine.render_frame(timeline, t=1.0)

        # Fixture 1 at address 1: channels 1-4 (address + offsets 0-3)
        assert result[1][1] == 255  # dimmer
        assert result[1][2] == 255  # red
        assert result[1][3] == 0    # green
        assert result[1][4] == 0    # blue

        # Fixture 2 at address 10: channels 10-13 (address + offsets 0-3)
        assert result[1][10] == 255  # dimmer
        assert result[1][11] == 255  # red
        assert result[1][12] == 0    # green
        assert result[1][13] == 0    # blue

    def test_render_with_selector(self, two_fixture_rig: Rig) -> None:
        """Selector applies only to matching fixtures."""
        engine = DMXEngine(rig=two_fixture_rig)
        scene = SceneClip(
            selector=lambda rig: rig.by_tag("left"),
            params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 1.0, 1.0)),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=10.0,
        )
        timeline = TimelineClip().add(0.0, scene)
        result = engine.render_frame(timeline, t=1.0)

        # Left fixture (address 1) should be lit
        assert result[1][1] == 255

        # Right fixture (address 10) should remain at 0
        assert result[1][10] == 0


class TestDMXEngineStop:
    """Tests for engine stop functionality."""

    def test_stop_sets_running_false(self, simple_rig: Rig) -> None:
        """Stop sets _running to False."""
        engine = DMXEngine(rig=simple_rig)
        engine._running = True
        engine.stop()
        assert engine._running is False


class TestDMXEngineInitialization:
    """Tests for engine initialization."""

    def test_default_fps(self, simple_rig: Rig) -> None:
        """Default FPS is 40."""
        engine = DMXEngine(rig=simple_rig)
        assert engine.fps == 40.0

    def test_custom_fps(self, simple_rig: Rig) -> None:
        """Custom FPS is respected."""
        engine = DMXEngine(rig=simple_rig, fps=60.0)
        assert engine.fps == 60.0

    def test_default_universe(self, simple_rig: Rig) -> None:
        """Default universe is [1]."""
        engine = DMXEngine(rig=simple_rig)
        assert engine.universe_ids == [1]

    def test_fixture_states_initialized(self, simple_rig: Rig) -> None:
        """Fixture states are initialized for all fixtures."""
        engine = DMXEngine(rig=simple_rig)
        assert len(engine._fixture_states) == len(simple_rig.all)
        for state in engine._fixture_states.values():
            assert state.dimmer == 0.0
            assert state.rgb == (0.0, 0.0, 0.0)

    def test_optional_rig(self) -> None:
        """Engine can be created without rig."""
        engine = DMXEngine()
        assert engine.rig is None
        assert len(engine._fixture_states) == 0

    def test_set_rig(self, simple_rig: Rig) -> None:
        """set_rig initializes fixture states."""
        engine = DMXEngine()
        engine.set_rig(simple_rig)
        assert engine.rig is simple_rig
        assert len(engine._fixture_states) == len(simple_rig.all)


class TestDMXEngineWithFixtureContext:
    """Tests for auto-collected fixtures with engine."""

    def test_collected_fixtures_work_with_engine(self) -> None:
        """Fixtures collected via context work correctly with engine."""
        ft = MockFixtureType()
        with FixtureContext() as ctx:
            f1 = Fixture(ft, 1, 1, tags={"all"})
            f2 = Fixture(ft, 1, 10, tags={"all"})

        rig = Rig(ctx.fixtures)
        engine = DMXEngine(rig=rig)

        scene = SceneClip(
            selector=[f1, f2],  # Use collected fixtures directly
            params_fn=FixtureState(dimmer=1.0, rgb=(1.0, 1.0, 1.0)),
            fade_in=0.0,
            fade_out=0.0,
            clip_duration=10.0,
        )
        timeline = TimelineClip().add(0.0, scene)
        result = engine.render_frame(timeline, t=1.0)

        assert result[1][1] == 255
        assert result[1][10] == 255
