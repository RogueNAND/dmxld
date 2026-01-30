# dmxld

DMX lighting control library with sACN and Art-Net support.

## Installation

```bash
pip install dmxld
pip install sacn            # For sACN (E1.31)
pip install stupidArtnet    # For Art-Net
```

## Getting Started

This tutorial walks through building fixtures, scenes, and effects.

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

### Step 3: Render and Send DMX

The `DMXEngine` renders clips to DMX values and sends them over the network:

```python
from dmxld import DMXEngine

engine = DMXEngine(rig=rig)

# Render a single frame at time t
dmx_data = engine.render_frame(red_scene, t=1.0)
# {1: {1: 255, 2: 255, 3: 0, 4: 0}}

# Send to lights
engine.start()          # Open network connection
engine.send(dmx_data)   # Send DMX data
engine.stop()           # Close connection
```

### Step 4: Build Your Own Playback Loop

dmxld focuses on rendering - you control the playback loop:

```python
import time

engine = DMXEngine(rig=rig)
engine.start()

t = 0.0
while t < red_scene.duration:
    dmx_data = engine.render_frame(red_scene, t)
    engine.send(dmx_data)
    time.sleep(1/40)  # 40 fps
    t += 1/40

engine.stop()
```

For more sophisticated show programming with timelines, tempo sync, and scheduling, see the [timeline](https://github.com/youruser/timeline) library which integrates seamlessly with dmxld.

## Dynamic Effects

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

## Blending

Use `blend_op` to control how clips combine when layered:

```python
from dmxld import BlendOp

# Pulsing dimmer that multiplies with the base value
pulse_modifier = EffectClip(
    selector=lambda r: r.all,
    params_fn=lambda t, f, i: FixtureState(
        dimmer=0.5 + 0.5 * math.sin(t * 2 * math.pi)
    ),
    clip_duration=10.0,
    blend_op=BlendOp.MUL,
)
```

| BlendOp | Description |
|---------|-------------|
| `SET` | Overwrite (default) |
| `MUL` | Multiply with existing value |
| `ADD_CLAMP` | Add and clamp to 0-1 |

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

Use `render_frame` to see what DMX values would be sent without transmitting:

```python
dmx_data = engine.render_frame(red_scene, t=1.5)
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

### DMXEngine API

```python
engine = DMXEngine(
    rig=rig,
    protocol=Protocol.SACN,  # or Protocol.ARTNET
    fps=40.0,
    universe_ips={},         # Optional unicast IPs per universe
    artnet_target="255.255.255.255",  # Art-Net broadcast target
)

# Rendering
dmx_data = engine.render_frame(clip, t)  # Returns {universe: {channel: value}}

# Transport control
engine.start()              # Open network connection
engine.send(dmx_data)       # Send DMX data
engine.stop()               # Close connection

# Rig management
engine.set_rig(new_rig)     # Change rig after creation
```
