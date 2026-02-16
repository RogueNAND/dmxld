"""Clip system for dmxld."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Protocol

from dmxld.blend import BlendOp, FixtureDelta
from dmxld.model import Fixture, FixtureState, Rig


class Clip(Protocol):
    """Protocol for clips that can be rendered."""

    @property
    def duration(self) -> float | None:
        """Duration in seconds, or None for infinite."""
        ...

    def render(self, t: float, rig: Rig) -> dict[Fixture, FixtureDelta]:
        """Render the clip at time t, returning deltas for affected fixtures."""
        ...


Selector = Callable[[Rig], Iterable[Fixture]]
ParamsFn = Callable[[Fixture], FixtureState]


def fade(
    t: float, duration: float | None, fade_in: float, fade_out: float
) -> float:
    """Calculate fade multiplier for time t (units are generic — same unit as t)."""
    if fade_in > 0 and t < fade_in:
        return t / fade_in
    if duration is not None and fade_out > 0:
        time_remaining = duration - t
        if time_remaining < fade_out:
            return max(0.0, time_remaining / fade_out)
    return 1.0


Layer = tuple[Selector | Iterable[Fixture], ParamsFn | FixtureState]


@dataclass
class Scene:
    """Static lighting look — no time dependency.

    Defines what lights look like via layers of (selector, state) pairs.
    Fading and timeline integration are handled externally.

    Can be created with a single selector/params pair, or with multiple layers:

        # Single layer
        Scene(selector=front, params=FixtureState(dimmer=1.0))

        # Multi-layer form
        Scene(layers=[
            (front, FixtureState(dimmer=1.0, color=(1,0,0))),
            (back,  lambda f: FixtureState(dimmer=0.5, color=(0,0,1))),
        ])

    When layers overlap (same fixture in multiple layers), later layers overwrite
    earlier ones per attribute.

    Args:
        selector: Fixture selector (single-layer form).
        params: Parameters function or static state (single-layer form).
        layers: List of (selector, params) tuples (multi-layer form).
        blend_op: How to combine with other clips (SET overwrites, MUL multiplies,
                  ADD_CLAMP adds). Defaults to SET.
    """

    selector: Selector | Iterable[Fixture] | None = None
    params: ParamsFn | FixtureState | None = None
    layers: list[Layer] | None = None
    blend_op: BlendOp = BlendOp.SET

    def __post_init__(self) -> None:
        has_single = self.selector is not None or self.params is not None
        has_layers = self.layers is not None
        if has_single and has_layers:
            raise ValueError("Use either selector/params or layers, not both")
        if not has_single and not has_layers:
            raise ValueError("Provide selector/params or layers")
        if has_single and (self.selector is None or self.params is None):
            raise ValueError("Both selector and params are required")
        self._resolved_layers = self._resolve_layers()
        self._render_cache = None

    def _resolve_layers(self) -> list[tuple[Selector, ParamsFn]]:
        """Normalize single or multi-layer form into list of (selector_fn, params_fn)."""
        if self.layers is not None:
            raw = self.layers
        else:
            raw = [(self.selector, self.params)]
        result = []
        for sel, par in raw:
            selector_fn = sel if callable(sel) else lambda r, s=sel: s
            params_fn = par if callable(par) else lambda f, p=par: p
            result.append((selector_fn, params_fn))
        return result

    def render(self, rig: Rig) -> dict[Fixture, FixtureDelta]:
        if self._render_cache is not None:
            return self._render_cache
        result: dict[Fixture, FixtureDelta] = {}
        for selector_fn, params_fn in self._resolved_layers:
            for fixture in selector_fn(rig):
                state = params_fn(fixture)
                delta = result.get(fixture) or FixtureDelta()
                for name, value in state.items():
                    delta[name] = (self.blend_op, value)
                result[fixture] = delta
        self._render_cache = result
        return result


# Type for effect params function: (t, fixture, index, segment) -> FixtureState
EffectParamsFn = Callable[[float, Fixture, int, int], FixtureState]


@dataclass
class EffectClip:
    """Math-driven effect with access to time, fixture, index, and segment.

    The params function receives (t, fixture, index, segment) allowing per-fixture
    and per-segment effects based on time, position, or iteration order.

    For segmented fixtures (e.g., LED bars with multiple color zones), the params
    function is called once per segment. The segment index can be used to create
    per-segment animations. Non-segmented fixtures always have segment=0.

    Args:
        blend_op: How to combine with other clips (SET overwrites, MUL multiplies,
                  ADD_CLAMP adds). Defaults to SET. Use MUL to layer dimmer
                  modulation on top of other clips.

    Example - color wave across fixtures by X position:
        EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(
                dimmer=1.0,
                color=Color.from_hsv((t * 0.2 + f.pos.x * 0.1) % 1.0, 1.0, 1.0)
            ),
            clip_duration=10.0,
        )

    Example - rainbow across segments:
        EffectClip(
            selector=lambda r: r.all,
            params=lambda t, f, i, seg: FixtureState(
                color=Color.from_hsv((t + seg * 0.25) % 1.0, 1.0, 1.0)
            ),
            clip_duration=10.0,
        )
    """

    selector: Selector | Iterable[Fixture]
    params: EffectParamsFn
    fade_in: float = 0.0
    fade_out: float = 0.0
    clip_duration: float | None = None
    blend_op: BlendOp = BlendOp.SET

    @property
    def duration(self) -> float | None:
        return self.clip_duration

    def render(self, t: float, rig: Rig) -> dict[Fixture, FixtureDelta]:
        if t < 0 or (self.clip_duration is not None and t > self.clip_duration):
            return {}

        fade_mult = fade(t, self.clip_duration, self.fade_in, self.fade_out)
        selector_fn = self.selector if callable(self.selector) else lambda r: self.selector

        result: dict[Fixture, FixtureDelta] = {}
        for idx, fixture in enumerate(selector_fn(rig)):
            delta = FixtureDelta()
            segment_count = fixture.segment_count

            for seg in range(segment_count):
                state = self.params(t, fixture, idx, seg)

                for name, value in state.items():
                    if name == "dimmer":
                        if seg == 0:
                            delta[name] = (self.blend_op, value * fade_mult)
                    elif name == "color" and segment_count > 1:
                        delta[f"color_{seg}"] = (self.blend_op, value)
                    else:
                        delta[name] = (self.blend_op, value)

            result[fixture] = delta
        return result
