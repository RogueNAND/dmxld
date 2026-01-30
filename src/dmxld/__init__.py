"""dmxld - DMX lighting control library."""

from dmxld.model import (
    Vec3,
    FixtureState,
    FixtureType,
    Fixture,
    FixtureContext,
    Rig,
)
from dmxld.blend import (
    BlendOp,
    FixtureDelta,
    apply_delta,
    merge_deltas,
    compose_lighting_deltas,
)
from dmxld.clips import Clip, SceneClip, EffectClip, TimelineClip, LightingTimeline
from dmxld.engine import DMXEngine, Protocol

# Attributes
from dmxld.attributes import (
    DimmerAttr,
    RGBAttr,
    RGBWAttr,
    StrobeAttr,
    PanAttr,
    TiltAttr,
    GoboAttr,
    SkipAttr,
)

# Color
from dmxld.color import RGB, RGBW

# Re-export Timeline from timeline package for convenience
from timeline import Timeline

__all__ = [
    # Model
    "Vec3",
    "FixtureState",
    "FixtureType",
    "Fixture",
    "FixtureContext",
    "Rig",
    # Blend
    "BlendOp",
    "FixtureDelta",
    "apply_delta",
    "merge_deltas",
    "compose_lighting_deltas",
    # Clips
    "Clip",
    "SceneClip",
    "EffectClip",
    "TimelineClip",
    "LightingTimeline",
    "Timeline",
    # Engine
    "DMXEngine",
    "Protocol",
    # Attributes
    "DimmerAttr",
    "RGBAttr",
    "RGBWAttr",
    "StrobeAttr",
    "PanAttr",
    "TiltAttr",
    "GoboAttr",
    "SkipAttr",
    # Color
    "RGB",
    "RGBW",
]

__version__ = "0.1.0"
