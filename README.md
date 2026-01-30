# dmxld

DMX lighting control library with sACN and Art-Net support.

## Installation

```bash
pip install dmxld
```

Requires `sacn` and/or `stupidArtnet` depending on which protocol you use:

```bash
pip install sacn            # For sACN (E1.31)
pip install stupidArtnet    # For Art-Net
```

## Quick Start

```python
from dmxld import (
    DMXEngine, Rig, Fixture, FixtureType, DimmerAttr, RGBAttr,
    TimelineClip, SceneClip, FixtureState
)

# Define fixture type
RGBPar = FixtureType(DimmerAttr(), RGBAttr())

# Define fixtures
rig = Rig([
    Fixture(RGBPar, universe=1, address=1, tags={"front"}),
    Fixture(RGBPar, universe=1, address=5, tags={"front"}),
    Fixture(RGBPar, universe=1, address=9, tags={"back"}),
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

# Play (sACN multicast by default)
engine = DMXEngine(rig=rig)
engine.play_sync(show)
```

## Examples

### Defining Fixture Types

```python
from dmxld import FixtureType, DimmerAttr, RGBAttr, RGBWAttr, PanAttr, TiltAttr, StrobeAttr, SkipAttr

# Simple RGB par (4 channels: dimmer + RGB)
RGBPar = FixtureType(DimmerAttr(), RGBAttr())

# RGBW fixture (5 channels: dimmer + RGBW)
RGBWPar = FixtureType(DimmerAttr(), RGBWAttr())

# Moving head with 16-bit pan/tilt
MovingHead = FixtureType(
    DimmerAttr(),
    RGBAttr(),
    StrobeAttr(),
    PanAttr(fine=True),   # 16-bit (2 channels)
    TiltAttr(fine=True),  # 16-bit (2 channels)
)

# Skip unused channels in the fixture profile
WeirdFixture = FixtureType(
    DimmerAttr(),
    SkipAttr(2),  # 2 unused channels
    RGBAttr(),
)
```

**Available attributes:**

| Attribute | Channels | Notes |
|-----------|----------|-------|
| `DimmerAttr(fine=False)` | 1-2 | 8-bit or 16-bit |
| `RGBAttr()` | 3 | Red, Green, Blue |
| `RGBWAttr()` | 4 | Red, Green, Blue, White |
| `StrobeAttr()` | 1 | 0=off, 1=max |
| `PanAttr(fine=False)` | 1-2 | 8-bit or 16-bit |
| `TiltAttr(fine=False)` | 1-2 | 8-bit or 16-bit |
| `GoboAttr()` | 1 | Gobo wheel selection |
| `SkipAttr(count)` | n | Placeholder for unused channels |

### Fixtures and Rigs

```python
from dmxld import Fixture, Rig, FixtureType, DimmerAttr, RGBAttr, Vec3

RGBPar = FixtureType(DimmerAttr(), RGBAttr())

# Basic fixture
spot = Fixture(RGBPar, universe=1, address=1)

# With position and tags
wash = Fixture(
    RGBPar,
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
from dmxld import Fixture, FixtureContext, Rig, FixtureType, DimmerAttr, RGBAttr

RGBPar = FixtureType(DimmerAttr(), RGBAttr())

with FixtureContext() as ctx:
    Fixture(RGBPar, universe=1, address=1, tags={"front"})
    Fixture(RGBPar, universe=1, address=5, tags={"front"})
    Fixture(RGBPar, universe=1, address=9, tags={"back"})

rig = Rig(ctx.fixtures)
```

### SceneClip

Static scene with optional fades:

```python
from dmxld import SceneClip, FixtureState

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
from dmxld import DimmerPulseClip

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
from dmxld import TimelineClip, SceneClip, DimmerPulseClip, FixtureState

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

### Protocol Configuration

```python
from dmxld import DMXEngine, Protocol, Rig

# sACN (default) - uses E1.31 multicast
engine = DMXEngine(rig=rig, protocol=Protocol.SACN)

# Art-Net - broadcasts by default
engine = DMXEngine(rig=rig, protocol=Protocol.ARTNET)

# Art-Net with specific target IP
engine = DMXEngine(
    rig=rig,
    protocol=Protocol.ARTNET,
    artnet_target="192.168.1.100"
)

# Unicast to specific IPs per universe
engine = DMXEngine(
    rig=rig,
    protocol=Protocol.SACN,
    universe_ips={1: "192.168.1.100", 2: "192.168.1.101"}
)
```

### FixtureState

Dict-based state for flexible attribute access:

```python
from dmxld import FixtureState

# Create with keyword args
state = FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0))

# Dict-style access
state["pan"] = 0.5
state.get("dimmer")  # 1.0

# Extended state for moving heads
state = FixtureState(
    dimmer=1.0,
    rgbw=(1.0, 0.0, 0.0, 0.5),
    pan=0.25,
    tilt=0.75,
)
```

### Testing Without Network

Use `render_frame` to test without network output:

```python
from dmxld import DMXEngine, Rig, Fixture, FixtureType, DimmerAttr, RGBAttr, SceneClip, FixtureState

RGBPar = FixtureType(DimmerAttr(), RGBAttr())
rig = Rig([Fixture(RGBPar, universe=1, address=1)])
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
from dmxld import DMXEngine, Rig, Fixture, FixtureType, DimmerAttr, RGBAttr

RGBPar = FixtureType(DimmerAttr(), RGBAttr())

rig = Rig([
    Fixture(RGBPar, universe=1, address=1),
    Fixture(RGBPar, universe=2, address=1),
])

# Universes auto-detected from fixtures
engine = DMXEngine(rig=rig)
```

## API Reference

### Core Classes

| Class | Description |
|-------|-------------|
| `Fixture` | Physical light with type, universe, address, position, tags |
| `FixtureType` | Composable fixture definition built from attributes |
| `Rig` | Collection of fixtures with `all`, `by_tag()` helpers |
| `DMXEngine` | Renders clips and sends DMX via sACN or Art-Net |

### Clip Types

| Clip | Description |
|------|-------------|
| `SceneClip` | Static state with optional fade in/out |
| `DimmerPulseClip` | Sine wave modulation on dimmer |
| `TimelineClip` | Schedules child clips at specific times |

### Blend Operations

| BlendOp | Description |
|---------|-------------|
| `SET` | Overwrite value |
| `MUL` | Multiply (for dimming) |
| `ADD_CLAMP` | Add and clamp to 0-1 |

## License

MIT
