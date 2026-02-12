"""dmxld - DMX lighting control library."""

from dmxld.model import (
    Vec3,
    FixtureState,
    FixtureType,
    Fixture,
    FixtureGroup,
    Rig,
)
from dmxld.blend import (
    BlendOp,
    FixtureDelta,
    apply_delta,
    merge_deltas,
    scale_deltas,
)
from dmxld.clips import Clip, Scene, EffectClip, fade
from dmxld.engine import DMXEngine, Protocol

# Attributes
from dmxld.attributes import (
    DimmerAttr,
    RGBAttr,
    RGBWAttr,
    RGBAAttr,
    RGBAWAttr,
    StrobeAttr,
    PanAttr,
    TiltAttr,
    GoboAttr,
    SkipAttr,
)

# Color
from dmxld.color import Color, Raw, rgb, set_color_strategy

__all__ = [
    # Model
    "Vec3",
    "FixtureState",
    "FixtureType",
    "Fixture",
    "FixtureGroup",
    "Rig",
    # Blend
    "BlendOp",
    "FixtureDelta",
    "apply_delta",
    "merge_deltas",
    "scale_deltas",
    # Clips
    "Clip",
    "Scene",
    "EffectClip",
    "fade",
    # Engine
    "DMXEngine",
    "Protocol",
    # Attributes
    "DimmerAttr",
    "RGBAttr",
    "RGBWAttr",
    "RGBAAttr",
    "RGBAWAttr",
    "StrobeAttr",
    "PanAttr",
    "TiltAttr",
    "GoboAttr",
    "SkipAttr",
    # Color
    "Color",
    "Raw",
    "rgb",
    "set_color_strategy",
]

__version__ = "0.1.0"
