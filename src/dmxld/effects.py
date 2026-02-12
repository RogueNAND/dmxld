"""Built-in effect templates for dmxld."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterable

from dmxld.clips import EffectClip, Selector
from dmxld.color import Color
from dmxld.model import Fixture, FixtureState

if TYPE_CHECKING:
    from dmxld.model import FixtureGroup


class EffectTemplate:
    """Base class for effect templates.

    Subclasses should be dataclasses and override render_params().

    Example:
        @dataclass
        class MyEffect(EffectTemplate):
            speed: float = 1.0

            def render_params(self, t: float, f: Fixture, i: int, seg: int) -> FixtureState:
                return FixtureState(dimmer=math.sin(t * self.speed))

        # Usage
        clip = MyEffect(speed=2.0)(front, duration=10.0)
    """

    def render_params(self, t: float, f: Fixture, i: int, seg: int) -> FixtureState:
        """Override to define the effect behavior.

        Args:
            t: Time since clip start (units match render's t)
            f: The fixture being rendered
            i: Index of the fixture in the selector order
            seg: Segment index within the fixture (0 for non-segmented fixtures)

        Returns:
            FixtureState with the attribute values for this frame
        """
        raise NotImplementedError

    @property
    def name(self) -> str:
        """Effect name derived from class and attributes."""
        cls_name = self.__class__.__name__
        if hasattr(self, "__dataclass_fields__"):
            fields = self.__dataclass_fields__
            params = ", ".join(f"{k}={getattr(self, k)}" for k in fields)
            return f"{cls_name}({params})" if params else cls_name
        return cls_name

    def create(
        self,
        selector: Selector | FixtureGroup | Iterable[Fixture],
        duration: float | None = None,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
    ) -> EffectClip:
        """Create an EffectClip from this template."""
        return EffectClip(
            selector=selector,
            params=self.render_params,
            clip_duration=duration,
            fade_in=fade_in,
            fade_out=fade_out,
        )

    def __call__(
        self,
        selector: Selector | FixtureGroup | Iterable[Fixture],
        duration: float | None = None,
        fade_in: float = 0.0,
        fade_out: float = 0.0,
    ) -> EffectClip:
        """Create an EffectClip from this template (shorthand for create)."""
        return self.create(selector, duration, fade_in, fade_out)

    def __repr__(self) -> str:
        return self.name


# -----------------------------------------------------------------------------
# Built-in effects
# -----------------------------------------------------------------------------


@dataclass
class Pulse(EffectTemplate):
    """Sinusoidal dimmer pulse effect.

    Args:
        rate: Pulses per second (Hz)

    Example:
        clip = Pulse(rate=2.0)(front, duration=10.0)
    """

    rate: float = 1.0

    def render_params(self, t: float, f: Fixture, i: int, seg: int) -> FixtureState:
        value = 0.5 + 0.5 * math.sin(t * self.rate * 2 * math.pi)
        return FixtureState(dimmer=value)


@dataclass
class Chase(EffectTemplate):
    """Chase effect that lights fixtures in sequence.

    Args:
        fixture_count: Number of fixtures in the chase
        speed: Chases per second
        width: Width of the lit section (1.0 = one fixture at a time)

    Example:
        clip = Chase(fixture_count=8, speed=2.0)(back, duration=10.0)
    """

    fixture_count: int
    speed: float = 1.0
    width: float = 1.0

    def render_params(self, t: float, f: Fixture, i: int, seg: int) -> FixtureState:
        position = (t * self.speed) % self.fixture_count
        distance = abs(i - position)
        distance = min(distance, self.fixture_count - distance)
        value = max(0.0, 1.0 - distance / self.width)
        return FixtureState(dimmer=value)


@dataclass
class Rainbow(EffectTemplate):
    """Rainbow color cycle effect.

    Args:
        speed: Color cycles per second
        saturation: Color saturation (0.0-1.0)

    Example:
        clip = Rainbow(speed=0.2)(front | back, duration=10.0)
    """

    speed: float = 0.1
    saturation: float = 1.0

    def render_params(self, t: float, f: Fixture, i: int, seg: int) -> FixtureState:
        # Phase by fixture index and segment for smooth rainbow across segments
        hue = (t * self.speed + i * 0.1 + seg * 0.05) % 1.0
        color = Color.from_hsv(hue, self.saturation, 1.0)
        return FixtureState(dimmer=1.0, color=color)


@dataclass
class Strobe(EffectTemplate):
    """Strobe effect with adjustable rate and duty cycle.

    Args:
        rate: Flashes per second (Hz)
        duty: Duty cycle (0.0-1.0), fraction of time the light is on

    Example:
        clip = Strobe(rate=10.0, duty=0.3)(front, duration=5.0)
    """

    rate: float = 10.0
    duty: float = 0.5

    def render_params(self, t: float, f: Fixture, i: int, seg: int) -> FixtureState:
        phase = (t * self.rate) % 1.0
        value = 1.0 if phase < self.duty else 0.0
        return FixtureState(dimmer=value)


@dataclass
class Wave(EffectTemplate):
    """Wave effect that travels across fixtures by index.

    Args:
        speed: Waves per second
        wavelength: Number of fixtures per wave cycle

    Example:
        clip = Wave(speed=0.5, wavelength=8.0)(front, duration=10.0)
    """

    speed: float = 1.0
    wavelength: float = 4.0

    def render_params(self, t: float, f: Fixture, i: int, seg: int) -> FixtureState:
        phase = t * self.speed - i / self.wavelength
        value = 0.5 + 0.5 * math.sin(phase * 2 * math.pi)
        return FixtureState(dimmer=value)


@dataclass
class Solid(EffectTemplate):
    """Solid color/dimmer effect (static, useful as base layer).

    Args:
        dimmer: Dimmer value (0.0-1.0)
        color: Optional color (RGB tuple or Color object)

    Example:
        clip = Solid(dimmer=0.8, color=(1.0, 0.5, 0.0))(front, duration=10.0)
    """

    dimmer: float = 1.0
    color: tuple[float, float, float] | Color | None = None

    def render_params(self, t: float, f: Fixture, i: int, seg: int) -> FixtureState:
        state = FixtureState(dimmer=self.dimmer)
        if self.color is not None:
            state["color"] = self.color
        return state
