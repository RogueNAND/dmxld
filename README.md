# dmxld

DMX lighting control library with sACN and Art-Net support.

## Installation

```bash
pip install dmxld
pip install sacn            # For sACN (E1.31)
pip install stupidArtnet    # For Art-Net
```

## Getting Started

This tutorial walks through building a complete lighting show. We'll start with the basics and progressively add features.

### Step 1: Define Your Fixtures

First, define what types of fixtures you have. A fixture type describes the DMX channel layout:

```python
from dmxld import FixtureType, DimmerAttr, RGBAttr

# A simple RGB par: 4 channels (dimmer + RGB)
RGBPar = FixtureType(DimmerAttr(), RGBAttr())
```

Now create the actual fixtures in your rig. Each fixture needs a universe, address, and optionally tags for grouping:

```python
from dmxld import Fixture, Rig

rig = Rig([
    Fixture(RGBPar, universe=1, address=1, tags={"front"}),
    Fixture(RGBPar, universe=1, address=5, tags={"front"}),
    Fixture(RGBPar, universe=1, address=9, tags={"back"}),
])
```

### Step 2: Create a Scene

A `SceneClip` sets fixtures to a static state. The `selector` picks which fixtures to target, and `params_fn` returns the state for each fixture:

```python
from dmxld import SceneClip, FixtureState

red_scene = SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0)),
    clip_duration=3.0,
)
```

Add fades by specifying `fade_in` and `fade_out`:

```python
red_scene = SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0)),
    clip_duration=5.0,
    fade_in=1.0,
    fade_out=2.0,
)
```

Target specific fixtures using tags:

```python
front_only = SceneClip(
    selector=lambda r: r.by_tag("front"),
    params_fn=lambda f: FixtureState(dimmer=0.8, rgb=(1.0, 1.0, 1.0)),
    clip_duration=3.0,
)
```

### Step 3: Build a Timeline

Arrange clips on a `TimelineClip` to create a show:

```python
from dmxld import TimelineClip

show = TimelineClip()
show.add(0.0, SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0)),
    clip_duration=3.0,
    fade_in=1.0,
))
show.add(3.0, SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(0.0, 0.0, 1.0)),
    clip_duration=3.0,
    fade_out=1.0,
))
```

### Step 4: Play the Show

The `DMXEngine` renders clips and sends DMX data over the network:

```python
from dmxld import DMXEngine

engine = DMXEngine(rig=rig)
engine.play_sync(show)  # Blocks until complete
```

By default, dmxld uses sACN multicast. For Art-Net or unicast, see [Protocol Configuration](#protocol-configuration) below.

## Adding Dynamic Effects

For animations that change over time, use `EffectClip`. Its `params_fn` receives the current time `t`, the fixture `f`, and the fixture's index `i`:

```python
from dmxld import EffectClip
import math
import colorsys

# Pulsing dimmer
pulse = EffectClip(
    selector=lambda r: r.all,
    params_fn=lambda t, f, i: FixtureState(
        dimmer=0.5 + 0.5 * math.sin(t * 2 * math.pi),
        rgb=(1.0, 0.0, 0.0),
    ),
    clip_duration=10.0,
)

# Rainbow wave across fixtures
rainbow = EffectClip(
    selector=lambda r: r.all,
    params_fn=lambda t, f, i: FixtureState(
        dimmer=1.0,
        rgb=colorsys.hsv_to_rgb((t * 0.1 + i * 0.125) % 1.0, 1.0, 1.0),
    ),
    clip_duration=10.0,
)

# Chase sequence
chase = EffectClip(
    selector=lambda r: r.all,
    params_fn=lambda t, f, i: FixtureState(
        dimmer=1.0 if int(t * 4) % 8 == i else 0.0,
        rgb=(1.0, 0.0, 0.0),
    ),
    clip_duration=10.0,
)
```

Effects can overlap with scenes on the timeline. Use `blend_op` to control how they combine:

```python
from dmxld import BlendOp

show = TimelineClip()

# Base color
show.add(0.0, SceneClip(
    selector=lambda r: r.all,
    params_fn=lambda f: FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0)),
    clip_duration=10.0,
))

# Pulsing dimmer that multiplies with the base
show.add(0.0, EffectClip(
    selector=lambda r: r.all,
    params_fn=lambda t, f, i: FixtureState(
        dimmer=0.5 + 0.5 * math.sin(t * 2 * math.pi)
    ),
    clip_duration=10.0,
    blend_op=BlendOp.MUL,
))
```

| BlendOp | Description |
|---------|-------------|
| `SET` | Overwrite (default) |
| `MUL` | Multiply with existing value |
| `ADD_CLAMP` | Add and clamp to 0-1 |

## Syncing to Music with BPM

For music-synced shows, use `BPMTimeline` to schedule clips at beat positions instead of seconds:

```python
from dmxld import BPMTimeline, TempoMap, compose_lighting_deltas

tempo = TempoMap(128)  # 128 BPM
show = BPMTimeline(compose_fn=compose_lighting_deltas, tempo_map=tempo)

show.add(0, intro_scene)    # Beat 0
show.add(16, verse_scene)   # Beat 16
show.add(32, chorus_scene)  # Beat 32
```

For songs with tempo changes, call `set_tempo` at the beat where the tempo changes:

```python
tempo = TempoMap(120)
tempo.set_tempo(64, 140)   # Speed up at beat 64
tempo.set_tempo(128, 100)  # Slow down at beat 128
```

To sync effects to the beat, use `tempo.beat(t)` in your params_fn:

```python
strobe = EffectClip(
    selector=lambda r: r.all,
    params_fn=lambda t, f, i: FixtureState(
        dimmer=1.0 if int(tempo.beat(t)) % 2 == 0 else 0.0,
        rgb=(1.0, 1.0, 1.0),
    ),
    clip_duration=tempo.time(32),  # 32 beats
)
```

## Protocol Configuration

```python
from dmxld import DMXEngine, Protocol

# sACN multicast (default)
engine = DMXEngine(rig=rig, protocol=Protocol.SACN)

# Art-Net broadcast
engine = DMXEngine(rig=rig, protocol=Protocol.ARTNET)

# Art-Net to specific IP
engine = DMXEngine(rig=rig, protocol=Protocol.ARTNET, artnet_target="192.168.1.100")

# sACN unicast per universe
engine = DMXEngine(rig=rig, protocol=Protocol.SACN, universe_ips={1: "192.168.1.100"})
```

## Testing Without Hardware

Use `render_frame` to see what DMX values would be sent without actually transmitting:

```python
dmx_data = engine.render_frame(show, t=1.5)
print(dmx_data)
# {1: {1: 255, 2: 255, 3: 0, 4: 0}}
```

## Reference

### Fixture Types

Build fixture types by composing attributes:

```python
from dmxld import FixtureType, DimmerAttr, RGBAttr, RGBWAttr, PanAttr, TiltAttr, StrobeAttr, SkipAttr

RGBPar = FixtureType(DimmerAttr(), RGBAttr())
RGBWPar = FixtureType(DimmerAttr(), RGBWAttr())
MovingHead = FixtureType(
    DimmerAttr(),
    RGBAttr(),
    StrobeAttr(),
    PanAttr(fine=True),   # 16-bit
    TiltAttr(fine=True),  # 16-bit
)

# Skip unused channels in a profile
WeirdFixture = FixtureType(DimmerAttr(), SkipAttr(2), RGBAttr())
```

| Attribute | Channels | Notes |
|-----------|----------|-------|
| `DimmerAttr(fine=False)` | 1-2 | 8 or 16-bit |
| `RGBAttr()` | 3 | Red, Green, Blue |
| `RGBWAttr()` | 4 | Red, Green, Blue, White |
| `StrobeAttr()` | 1 | 0=off, 1=max |
| `PanAttr(fine=False)` | 1-2 | 8 or 16-bit |
| `TiltAttr(fine=False)` | 1-2 | 8 or 16-bit |
| `GoboAttr()` | 1 | Gobo wheel |
| `SkipAttr(count)` | n | Unused channels |

### FixtureState

All values are normalized 0.0-1.0:

```python
from dmxld import FixtureState

state = FixtureState(dimmer=1.0, rgb=(1.0, 0.0, 0.0))
state = FixtureState(dimmer=1.0, rgbw=(1.0, 0.0, 0.0, 0.5), pan=0.25, tilt=0.75)

# Dict-style access
state["pan"] = 0.5
state.get("dimmer")
```

### FixtureContext

Automatically collect fixtures as they're created:

```python
from dmxld import FixtureContext

with FixtureContext() as ctx:
    Fixture(RGBPar, universe=1, address=1, tags={"front"})
    Fixture(RGBPar, universe=1, address=5, tags={"front"})

rig = Rig(ctx.fixtures)
```

### Fixture Positioning

Use `Vec3` for spatial effects:

```python
from dmxld import Vec3

wash = Fixture(RGBPar, universe=1, address=5, pos=Vec3(x=0.0, y=2.0, z=0.0))

# Use position in effects
wave = EffectClip(
    selector=lambda r: r.all,
    params_fn=lambda t, f, i: FixtureState(
        dimmer=1.0,
        rgb=colorsys.hsv_to_rgb((t * 0.2 + f.pos.x * 0.1) % 1.0, 1.0, 1.0),
    ),
    clip_duration=10.0,
)
```

## License

MIT
