# Creating Shows

A show in FCLD consists of three parts: a **Rig** (your fixtures), **Clips** (lighting effects), and a **Timeline** (when clips play).

## Basic Structure

```python
from fcld import (
    DMXEngine, Fixture, FixtureState, GenericRGBDimmer,
    Rig, SceneClip, DimmerPulseClip, TimelineClip, Vec3,
)

# 1. Define your rig
def create_rig() -> Rig:
    fixture = Fixture(
        name="front_wash",
        fixture_type=GenericRGBDimmer(),
        universe=1,
        address=1,
        pos=Vec3(x=0.0, y=0.0, z=3.0),
        tags={"wash", "front"},
    )
    return Rig([fixture])

# 2. Create selectors (functions that pick fixtures)
def all_fixtures(rig: Rig) -> list[Fixture]:
    return rig.all

def by_tag_wash(rig: Rig) -> list[Fixture]:
    return rig.by_tag("wash")

# 3. Create palettes (functions that return colors/states)
def red(_fixture: Fixture) -> FixtureState:
    return FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0))

# 4. Build your timeline
def create_show() -> TimelineClip:
    timeline = TimelineClip()

    # Add a scene at t=0
    scene = SceneClip(
        selector=all_fixtures,
        params_fn=red,
        fade_in=2.0,
        fade_out=2.0,
        clip_duration=10.0,
    )
    timeline.add(0.0, scene)

    # Add a pulse effect at t=3
    pulse = DimmerPulseClip(
        selector=all_fixtures,
        rate_hz=1.0,      # pulses per second
        depth=0.3,        # amplitude
        base=0.7,         # center value
        clip_duration=5.0,
    )
    timeline.add(3.0, pulse)

    return timeline

# 5. Run function
def run(start_at: float = 0.0, fps: float = 40.0) -> None:
    rig = create_rig()
    show = create_show()
    engine = DMXEngine(rig=rig, universe_ids=[1], fps=fps)
    engine.play(show, start_at=start_at)

if __name__ == "__main__":
    run()
```

## Clip Types

| Clip | Purpose |
|------|---------|
| `SceneClip` | Static look with fade in/out |
| `DimmerPulseClip` | Sine wave pulse on dimmer (multiplies existing value) |
| `TimelineClip` | Container that schedules other clips |

## Launching Shows

**Prerequisites:** OLA daemon must be running on host (`olad -l 3`).

```bash
# Run the built-in demo
PYTHONPATH=src:. python3 -m fcld.cli demo-basic

# Run your own show file
PYTHONPATH=src:. python3 shows/my_show.py

# With Docker (connects to OLA on host)
docker run --rm fcld demo                                  # Mac/Windows
docker run --rm --network host -e OLA_HOST=127.0.0.1 fcld demo  # Linux
docker run --rm -e OLA_HOST=192.168.1.100 fcld demo        # Remote OLA

# Custom show with Docker
docker run --rm -v ./shows:/app/shows fcld run my_show.py
```

## Dry Run (No OLA)

Test rendering without hardware:

```bash
PYTHONPATH=src:. python3 -c "
from shows.my_show import create_rig, create_show
from fcld.engine import DMXEngine

engine = DMXEngine(rig=create_rig())
print(engine.render_frame(create_show(), t=5.0))
"
```
