"""Basic demo show with 2 fixtures, timeline, and selectors."""

from __future__ import annotations

from fcld import (
    DMXEngine,
    DimmerPulseClip,
    Fixture,
    FixtureState,
    GenericRGBDimmer,
    Rig,
    SceneClip,
    TimelineClip,
    Vec3,
)


def all_fixtures(rig: Rig) -> list[Fixture]:
    """Selector: all fixtures in the rig."""
    return rig.all


def left_side(rig: Rig) -> list[Fixture]:
    """Selector: fixtures with x < 0."""
    return [f for f in rig.all if f.pos.x < 0]


def right_side(rig: Rig) -> list[Fixture]:
    """Selector: fixtures with x >= 0."""
    return [f for f in rig.all if f.pos.x >= 0]


def warm_white(_fixture: Fixture) -> FixtureState:
    """Palette: warm white color at full dimmer."""
    return FixtureState(dimmer=1.0, rgb=(1.0, 0.8, 0.6))


def cool_blue(_fixture: Fixture) -> FixtureState:
    """Palette: cool blue color at full dimmer."""
    return FixtureState(dimmer=1.0, rgb=(0.3, 0.5, 1.0))


def create_rig() -> Rig:
    """Create the demo rig with 2 fixtures."""
    fixture_type = GenericRGBDimmer()

    fixture1 = Fixture(
        name="wash_left",
        fixture_type=fixture_type,
        universe=1,
        address=1,
        pos=Vec3(x=-2.0, y=0.0, z=3.0),
        tags={"wash", "front", "left"},
    )

    fixture2 = Fixture(
        name="wash_right",
        fixture_type=fixture_type,
        universe=1,
        address=5,
        pos=Vec3(x=2.0, y=0.0, z=3.0),
        tags={"wash", "front", "right"},
    )

    return Rig([fixture1, fixture2])


def create_show() -> TimelineClip:
    """Create the demo show timeline."""
    timeline = TimelineClip()

    scene1 = SceneClip(
        selector=all_fixtures,
        params_fn=warm_white,
        fade_in=2.0,
        fade_out=2.0,
        clip_duration=10.0,
    )
    timeline.add(0.0, scene1)

    pulse1 = DimmerPulseClip(
        selector=left_side,
        rate_hz=0.5,
        depth=0.3,
        base=0.7,
        clip_duration=8.0,
    )
    timeline.add(2.0, pulse1)

    scene2 = SceneClip(
        selector=right_side,
        params_fn=cool_blue,
        fade_in=1.0,
        fade_out=1.0,
        clip_duration=5.0,
    )
    timeline.add(5.0, scene2)

    pulse2 = DimmerPulseClip(
        selector=all_fixtures,
        rate_hz=2.0,
        depth=0.2,
        base=0.8,
        clip_duration=3.0,
    )
    timeline.add(8.0, pulse2)

    return timeline


def run(start_at: float = 0.0, fps: float = 40.0) -> None:
    """Run the demo show."""
    rig = create_rig()
    show = create_show()

    engine = DMXEngine(rig=rig, universe_ids=[1], fps=fps)
    engine.play(show, start_at=start_at)


if __name__ == "__main__":
    run()
