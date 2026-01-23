"""Basic demo show with 2 fixtures, timeline, and selectors."""

from __future__ import annotations

from fcld import (
    DimmerPulseClip,
    Fixture,
    FixtureContext,
    FixtureState,
    GenericRGBDimmer,
    Rig,
    SceneClip,
    TimelineClip,
    Vec3,
    DMXEngine,
)


def run() -> TimelineClip:
    """Create and return the demo show.

    Fixtures are auto-collected by FixtureContext when called from server.
    """
    fixture_type = GenericRGBDimmer()

    wash_left = Fixture(
        fixture_type=fixture_type,
        universe=1,
        address=1,
        pos=Vec3(x=-2.0, y=0.0, z=3.0),
        tags={"wash", "front", "left"},
    )

    wash_right = Fixture(
        fixture_type=fixture_type,
        universe=1,
        address=5,
        pos=Vec3(x=2.0, y=0.0, z=3.0),
        tags={"wash", "front", "right"},
    )

    all_fixtures = [wash_left, wash_right]
    left_side = [wash_left]
    right_side = [wash_right]

    timeline = TimelineClip()

    # Scene 1: Warm white fade in on all fixtures
    timeline.add(0.0, SceneClip(
        selector=all_fixtures,
        params_fn=FixtureState(dimmer=1.0, rgb=(1.0, 0.8, 0.6)),
        fade_in=2.0,
        fade_out=2.0,
        clip_duration=10.0,
    ))

    # Pulse on left side
    timeline.add(2.0, DimmerPulseClip(
        selector=left_side,
        rate_hz=0.5,
        depth=0.3,
        base=0.7,
        clip_duration=8.0,
    ))

    # Scene 2: Cool blue on right side
    timeline.add(5.0, SceneClip(
        selector=right_side,
        params_fn=FixtureState(dimmer=1.0, rgb=(0.3, 0.5, 1.0)),
        fade_in=1.0,
        fade_out=1.0,
        clip_duration=5.0,
    ))

    # Final pulse on all
    timeline.add(8.0, DimmerPulseClip(
        selector=all_fixtures,
        rate_hz=2.0,
        depth=0.2,
        base=0.8,
        clip_duration=3.0,
    ))

    return timeline


if __name__ == "__main__":
    # For direct execution, manually wrap in FixtureContext
    with FixtureContext() as ctx:
        show = run()

    rig = Rig(ctx.fixtures)
    engine = DMXEngine(rig=rig, universe_ids=[1], fps=40.0)
    engine.play(show)
