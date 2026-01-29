"""dmxld - DMX Lighting Designer - DMX lighting control library."""

from dmxld.model import (
    Vec3,
    FixtureState,
    FixtureType,
    GenericRGBDimmer,
    Fixture,
    FixtureContext,
    Rig,
)
from dmxld.blend import BlendOp, FixtureDelta, apply_delta, merge_deltas
from dmxld.clips import Clip, SceneClip, DimmerPulseClip, TimelineClip
from dmxld.engine import DMXEngine, Protocol

__all__ = [
    "Vec3",
    "FixtureState",
    "FixtureType",
    "GenericRGBDimmer",
    "Fixture",
    "FixtureContext",
    "Rig",
    "BlendOp",
    "FixtureDelta",
    "apply_delta",
    "merge_deltas",
    "Clip",
    "SceneClip",
    "DimmerPulseClip",
    "TimelineClip",
    "DMXEngine",
    "Protocol",
]

__version__ = "0.1.0"
