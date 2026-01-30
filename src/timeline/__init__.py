"""Generic timeline library."""

from timeline.clip import Clip, Timeline, ComposeFn
from timeline.runner import Runner
from timeline.tempo import TempoMap, BPMTimeline

__all__ = ["Clip", "Timeline", "ComposeFn", "Runner", "TempoMap", "BPMTimeline"]

__version__ = "0.1.0"
