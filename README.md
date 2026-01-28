# olald

DMX lighting control library using [Open Lighting Architecture (OLA)](https://www.openlighting.org/ola/).

## Installation

```bash
pip install olald
```

Requires OLA Python bindings (`pip install ola`) and a running OLA daemon.

## OLA Connection

By default, olald connects to OLA via local Unix socket. For remote connections:

```bash
export OLA_HOST=192.168.1.100
export OLA_PORT=9010
```

## Quick Start

```python
from olald import DMXEngine, Rig, Fixture, GenericRGBDimmer, TimelineClip, SceneClip, FixtureState

# Define fixtures
rig = Rig([
    Fixture(GenericRGBDimmer(), universe=1, address=1, tags={"front"}),
    Fixture(GenericRGBDimmer(), universe=1, address=5, tags={"front"}),
    Fixture(GenericRGBDimmer(), universe=1, address=9, tags={"back"}),
])

# Build a show
show = TimelineClip()
show.add(0.0, SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0)),
    clip_duration=3.0,
    fade_in=1.0,
    fade_out=1.0,
))

# Play
engine = DMXEngine(rig=rig)
engine.play(show)
```

## Examples

### Fixtures and Rigs

```python
from olald import Fixture, Rig, GenericRGBDimmer, Vec3

# Basic fixture
spot = Fixture(GenericRGBDimmer(), universe=1, address=1)

# With position and tags
wash = Fixture(
    GenericRGBDimmer(),
    universe=1,
    address=5,
    pos=Vec3(x=0.0, y=2.0, z=0.0),
    tags={"wash", "stage-left"},
)

# Build rig
rig = Rig([spot, wash])

# Query fixtures
all_fixtures = rig.all
washes = rig.by_tag("wash")
```

### Using FixtureContext

Automatically collect fixtures as they're created:

```python
from olald import Fixture, FixtureContext, Rig, GenericRGBDimmer

with FixtureContext() as ctx:
    Fixture(GenericRGBDimmer(), universe=1, address=1, tags={"front"})
    Fixture(GenericRGBDimmer(), universe=1, address=5, tags={"front"})
    Fixture(GenericRGBDimmer(), universe=1, address=9, tags={"back"})

rig = Rig(ctx.fixtures)
```

### SceneClip

Static scene with optional fades:

```python
from olald import SceneClip, FixtureState

# All fixtures red at full
scene = SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0)),
    clip_duration=5.0,
)

# With fade in/out
scene = SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(0.0, 0.0, 1.0)),
    clip_duration=5.0,
    fade_in=1.0,
    fade_out=2.0,
)

# Target specific fixtures by tag
scene = SceneClip(
    selector=lambda r: r.by_tag("front"),
    params_fn=lambda f: FixtureState(dimmer=0.8, rgb=(1.0, 1.0, 1.0)),
    clip_duration=3.0,
)
```

### DimmerPulseClip

Sine wave modulation on dimmer:

```python
from olald import DimmerPulseClip

# Slow pulse on all fixtures
pulse = DimmerPulseClip(
    selector=lambda r: r.all,
    rate_hz=0.5,   # 0.5 Hz = 2 second cycle
    depth=0.4,     # Amplitude of pulse
    base=0.6,      # Center value
    clip_duration=10.0,
)
```

### TimelineClip

Sequence clips on a timeline:

```python
from olald import TimelineClip, SceneClip, DimmerPulseClip, FixtureState

show = TimelineClip()

# Red scene from 0-3s
show.add(0.0, SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0)),
    clip_duration=3.0,
))

# Blue scene from 3-6s
show.add(3.0, SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(0.0, 0.0, 1.0)),
    clip_duration=3.0,
))

# Overlapping pulse effect from 1-5s
show.add(1.0, DimmerPulseClip(
    selector=lambda r: r.by_tag("front"),
    rate_hz=2.0,
    clip_duration=4.0,
))

print(f"Show duration: {show.duration}s")
```

### Custom Fixture Types

Implement the `FixtureType` protocol:

```python
from olald import Fixture, FixtureState

class MovingHead:
    @property
    def name(self) -> str:
        return "MovingHead"

    @property
    def channel_count(self) -> int:
        return 8  # dimmer, R, G, B, pan, tilt, pan-fine, tilt-fine

    def encode(self, state: FixtureState) -> dict[int, int]:
        def to_dmx(v: float) -> int:
            return max(0, min(255, int(v * 255)))

        return {
            0: to_dmx(state.dimmer),
            1: to_dmx(state.rgb[0]),
            2: to_dmx(state.rgb[1]),
            3: to_dmx(state.rgb[2]),
            # Pan/tilt would need extended state
            4: 128,  # pan center
            5: 128,  # tilt center
            6: 0,
            7: 0,
        }

mover = Fixture(MovingHead(), universe=1, address=1)
```

### Testing Without OLA

Use `render_frame` to test without a running OLA daemon:

```python
from olald import DMXEngine, Rig, Fixture, GenericRGBDimmer, SceneClip, FixtureState

rig = Rig([Fixture(GenericRGBDimmer(), universe=1, address=1)])
engine = DMXEngine(rig=rig)

clip = SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.5, 0.0)),
    clip_duration=2.0,
)

# Render at t=1.0s
dmx_data = engine.render_frame(clip, t=1.0)
print(dmx_data)
# {1: {1: 255, 2: 255, 3: 127, 4: 0}}
```

### Multiple Universes

```python
from olald import DMXEngine, Rig, Fixture, GenericRGBDimmer

rig = Rig([
    Fixture(GenericRGBDimmer(), universe=1, address=1),
    Fixture(GenericRGBDimmer(), universe=2, address=1),
])

engine = DMXEngine(rig=rig, universe_ids=[1, 2])
```

## API Reference

### Core Classes

| Class | Description |
|-------|-------------|
| `Fixture` | Physical light with type, universe, address, position, tags |
| `Rig` | Collection of fixtures with `all`, `by_tag()` helpers |
| `DMXEngine` | Renders clips and sends DMX via OLA |

### Clip Types

| Clip | Description |
|------|-------------|
| `SceneClip` | Static state with optional fade in/out |
| `DimmerPulseClip` | Sine wave modulation on dimmer |
| `TimelineClip` | Schedules child clips at specific times |

### Fixture Types

| Type | Channels | Description |
|------|----------|-------------|
| `GenericRGBDimmer` | 4 | Dimmer, R, G, B (offsets 0-3) |

### Blend Operations

| BlendOp | Description |
|---------|-------------|
| `SET` | Overwrite value |
| `MUL` | Multiply (for dimming) |
| `ADD_CLAMP` | Add and clamp to 0-1 |

## License

MIT
