# dmxld

DMX lighting control library with sACN and Art-Net support.

```bash
pip install dmxld sacn          # sACN (E1.31)
pip install dmxld stupidArtnet  # Art-Net
```

## Quick Start

```python
from dmxld import (
    FixtureType, FixtureGroup, Rig, DMXEngine,
    DimmerAttr, RGBAttr, SceneClip, FixtureState
)
import time

# 1. Define groups and fixture types
front = FixtureGroup()
back = FixtureGroup()

FrontPar = FixtureType(DimmerAttr(), RGBAttr(), groups={front})
BackPar = FixtureType(DimmerAttr(), RGBAttr(), groups={back})

# 2. Create fixtures (FixtureType is callable)
rig = Rig([
    FrontPar(universe=1, address=1),
    FrontPar(universe=1, address=5),
    BackPar(universe=1, address=9),
])

# 3. Create a scene
scene = SceneClip(
    selector=front,
    params=lambda f: FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0)),
    clip_duration=5.0,
    fade_in=1.0,
)

# 4. Render and send
engine = DMXEngine(rig=rig)
engine.start()

t = 0.0
while t < scene.duration:
    engine.send(engine.render_frame(scene, t))
    time.sleep(1/40)
    t += 1/40

engine.stop()
```

### Multi-layer Scenes

Apply different states to different groups in a single scene with `layers`:

```python
scene = SceneClip(
    layers=[
        (front, FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))),
        (back,  lambda f: FixtureState(dimmer=0.5, color=(0.0, 0.0, 1.0))),
    ],
    clip_duration=5.0,
    fade_in=1.0,
)
```

Each layer is a `(selector, params)` tuple. When layers overlap, later layers overwrite earlier ones per attribute.

## Selectors

Groups work as selectors. Combine them with set operations:

```python
front | back      # Union (fixtures in either)
front & back      # Intersection (fixtures in both)
front + back      # Union (alias for |)
front - back      # Difference (in front but not back)
front ^ back      # Symmetric difference (in one but not both)

fixture in front  # Membership test
if front:         # True if non-empty

SceneClip(selector=front | back, ...)
SceneClip(selector=lambda r: r.all, ...)  # All fixtures in rig
```

## Built-in Effects

```python
from dmxld.effects import Pulse, Chase, Rainbow, Strobe, Wave, Solid

clip = Pulse(rate=2.0)(front, duration=10.0)
clip = Chase(fixture_count=8, speed=2.0)(back, duration=10.0)
clip = Rainbow(speed=0.2)(front | back, duration=10.0)
clip = Strobe(rate=10.0, duty=0.3)(front, duration=5.0)
clip = Wave(speed=1.0, wavelength=4.0)(front, duration=10.0)
clip = Solid(dimmer=0.8, color=(1.0, 0.5, 0.0))(front, duration=10.0)
```

## Custom Effects

`EffectClip` gives you access to time `t`, fixture `f`, index `i`, and segment `seg`:

```python
from dmxld import EffectClip
import math

pulse = EffectClip(
    selector=front,
    params=lambda t, f, i, seg: FixtureState(
        dimmer=0.5 + 0.5 * math.sin(t * 2 * math.pi),
        color=(1.0, 0.0, 0.0),
    ),
    clip_duration=10.0,
)
```

Create reusable templates:

```python
from dataclasses import dataclass
from dmxld.effects import EffectTemplate

@dataclass
class Flicker(EffectTemplate):
    intensity: float = 0.3

    def render_params(self, t: float, f, i: int, seg: int) -> FixtureState:
        import random
        return FixtureState(dimmer=1.0 - random.random() * self.intensity)

clip = Flicker(intensity=0.5)(front, duration=10.0)
```

## Blending

Layer effects with `blend_op`:

```python
from dmxld import BlendOp

# Dimmer modulation on top of another clip
modifier = EffectClip(
    selector=front,
    params=lambda t, f, i, seg: FixtureState(dimmer=0.5 + 0.5 * math.sin(t * 2 * math.pi)),
    clip_duration=10.0,
    blend_op=BlendOp.MUL,  # Multiplies with existing value
)
```

| BlendOp | Description |
|---------|-------------|
| `SET` | Overwrite (default) |
| `MUL` | Multiply |
| `ADD_CLAMP` | Add, clamp to 0-1 |

## Protocol Configuration

```python
from dmxld import Protocol

engine = DMXEngine(rig=rig, protocol=Protocol.SACN)   # Default, multicast
engine = DMXEngine(rig=rig, protocol=Protocol.ARTNET)  # Broadcast
engine = DMXEngine(rig=rig, protocol=Protocol.ARTNET, artnet_target="192.168.1.100")
```

## Testing Without Hardware

```python
dmx_data = engine.render_frame(scene, t=1.5)
print(dmx_data)  # {1: {1: 255, 2: 255, 3: 0, 4: 0}}
```

---

## Reference

### Attributes

| Attribute | Channels | Notes |
|-----------|----------|-------|
| `DimmerAttr(fine=False)` | 1-2 | 8 or 16-bit |
| `RGBAttr(segments=1)` | 3×n | Red, Green, Blue |
| `RGBWAttr(segments=1)` | 4×n | Red, Green, Blue, White |
| `RGBAAttr(segments=1)` | 4×n | Red, Green, Blue, Amber |
| `RGBAWAttr(segments=1)` | 5×n | Red, Green, Blue, Amber, White |
| `StrobeAttr()` | 1 | 0=off, 1=max |
| `PanAttr(fine=False)` | 1-2 | 8 or 16-bit |
| `TiltAttr(fine=False)` | 1-2 | 8 or 16-bit |
| `GoboAttr()` | 1 | Gobo wheel |
| `SkipAttr(count)` | n | Unused channels |

All color attributes respond to a unified `color=` key (see [Unified Color](#unified-color)).

```python
MovingHead = FixtureType(
    DimmerAttr(),
    RGBAttr(),
    PanAttr(fine=True),   # 16-bit
    TiltAttr(fine=True),
)
```

### Effects

| Effect | Parameters |
|--------|------------|
| `Pulse(rate)` | rate: Hz |
| `Chase(fixture_count, speed, width)` | fixture_count, speed: Hz, width |
| `Rainbow(speed, saturation)` | speed: cycles/sec, saturation |
| `Strobe(rate, duty)` | rate: Hz, duty: 0-1 |
| `Wave(speed, wavelength)` | speed: waves/sec, wavelength |
| `Solid(dimmer, color)` | dimmer: 0-1, color: tuple |

### FixtureState

All values normalized 0.0-1.0:

```python
state = FixtureState(dimmer=1.0, color=(1.0, 0.0, 0.0))
state["pan"] = 0.5
state.get("dimmer")
```

### Unified Color

Set `color=` once and it works on any fixture type—RGB, RGBW, RGBA, etc.:

```python
from dmxld import Color, FixtureState

# Same state works on RGB and RGBW fixtures
state = FixtureState(dimmer=1.0, color=(1.0, 0.5, 0.0))  # Orange
# RGB fixture:  R=255, G=127, B=0
# RGBW fixture: R=127, G=0, B=0, W=127 (white extracted)

# HSV input for hue-based effects
color = Color.from_hsv(h=0.0, s=1.0, v=1.0)  # Red
state = FixtureState(dimmer=1.0, color=color)

# Bypass conversion with Raw() wrapper
from dmxld import Raw
state = FixtureState(dimmer=1.0, color=Raw(0.5, 0.5, 0.5, 0.5))  # Exact RGBW values
```

Control white extraction strategy:

```python
from dmxld import set_color_strategy, RGBWAttr

set_color_strategy("balanced")      # Extract white from RGB (default)
set_color_strategy("preserve_rgb")  # Keep RGB as-is, white=0

# Per-fixture override
RGBWPar = FixtureType(DimmerAttr(), RGBWAttr(strategy="preserve_rgb"))
```

### Fixture Positioning

```python
from dmxld import Vec3

f = RGBPar(universe=1, address=5, pos=Vec3(x=0.0, y=2.0, z=0.0))

# Use in effects
params=lambda t, f, i, seg: FixtureState(
    dimmer=0.5 + 0.5 * math.sin(t + f.pos.x)
)
```

### Multi-Segment Fixtures

For fixtures with multiple color zones (LED bars, pixel strips):

```python
from dmxld import FixtureType, DimmerAttr, RGBWAttr, Raw

# LED bar with 4 independent RGBW segments (17 channels total)
LEDBar = FixtureType(DimmerAttr(), RGBWAttr(segments=4))

fixture = LEDBar(universe=1, address=1)
print(fixture.segment_count)  # 4
```

Effects receive a `seg` parameter (0 to segment_count-1):

```python
# Rainbow spread across segments
def rainbow_params(t, f, i, seg):
    hue = (t * 0.5 + seg / f.segment_count) % 1.0
    return FixtureState(dimmer=1.0, color=Color.from_hsv(hue, 1.0, 1.0))

# Per-segment control in FixtureState
state = FixtureState(
    dimmer=1.0,
    color_0=(1.0, 0.0, 0.0),  # Segment 0: red
    color_1=(0.0, 1.0, 0.0),  # Segment 1: green
    color_2=Raw(0.0, 0.0, 1.0, 0.5),  # Segment 2: direct RGBW
)
```
