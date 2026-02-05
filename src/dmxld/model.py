"""Data model layer for dmxld."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Iterator, Protocol
from weakref import WeakSet

if TYPE_CHECKING:
    from dmxld.model import Fixture, Rig


class FixtureGroup:
    """A group of fixtures that can be used as a selector.

    Groups are defined before fixtures and passed to fixtures via the groups parameter.
    Groups are callable (returning fixtures) and iterable.

    Examples:
        front = FixtureGroup()
        back = FixtureGroup()

        FrontPar = FixtureType(DimmerAttr(), RGBAttr(), groups={front})
        FrontPar(1, 1)

        # Use as selector
        SceneClip(selector=front, ...)

        # Iterate
        for f in front:
            ...

        # Compose groups
        all_stage = front | back    # union
        overlap = front & back      # intersection
    """

    def __init__(self) -> None:
        self._fixtures: WeakSet[Fixture] = WeakSet()

    def _add(self, fixture: Fixture) -> None:
        """Register a fixture with this group (called from Fixture.__post_init__)."""
        self._fixtures.add(fixture)

    def __call__(self, rig: Rig | None = None) -> list[Fixture]:
        """Return fixtures in this group (Selector protocol)."""
        return list(self._fixtures)

    def __iter__(self) -> Iterator[Fixture]:
        """Iterate over fixtures in this group."""
        return iter(self._fixtures)

    def __len__(self) -> int:
        """Number of fixtures in this group."""
        return len(self._fixtures)

    def __or__(self, other: FixtureGroup) -> FixtureGroup:
        """Union of two groups."""
        result = FixtureGroup()
        for f in self._fixtures:
            result._fixtures.add(f)
        for f in other._fixtures:
            result._fixtures.add(f)
        return result

    def __and__(self, other: FixtureGroup) -> FixtureGroup:
        """Intersection of two groups."""
        result = FixtureGroup()
        other_set = set(other._fixtures)
        for f in self._fixtures:
            if f in other_set:
                result._fixtures.add(f)
        return result

    def __repr__(self) -> str:
        return f"FixtureGroup({len(self._fixtures)} fixtures)"


class Attribute(Protocol):
    """Attribute protocol for type checking."""

    name: str
    channel_count: int
    default_value: Any

    def encode(self, value: Any) -> list[int]: ...


@dataclass(frozen=True)
class Vec3:
    """3D position vector."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


class FixtureState(dict[str, Any]):
    """Fixture state. Just a dict with keyword constructor."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(kwargs)

    def copy(self) -> FixtureState:
        return FixtureState(**self)

    def __repr__(self) -> str:
        items = ", ".join(f"{k}={v!r}" for k, v in self.items())
        return f"FixtureState({items})"


class FixtureType:
    """Composable fixture type built from attributes."""

    def __init__(
        self,
        *attributes: Attribute,
        groups: set[FixtureGroup] | None = None,
    ) -> None:
        self.attributes = attributes
        self.channel_count = sum(attr.channel_count for attr in attributes)
        self.default_groups = groups or set()

    def __call__(
        self,
        universe: int,
        address: int,
        pos: Vec3 | None = None,
        groups: set[FixtureGroup] | None = None,
        meta: dict[str, object] | None = None,
    ) -> Fixture:
        """Create a fixture of this type."""
        return Fixture(
            fixture_type=self,
            universe=universe,
            address=address,
            pos=pos or Vec3(),
            groups=set(self.default_groups) | (groups or set()),
            meta=meta or {},
        )

    def encode(self, state: FixtureState) -> dict[int, int]:
        """Encode state to DMX values (0-255).

        For color attributes, the priority is:
        1. raw_* key (e.g., raw_rgb, raw_rgbw) - explicit, no conversion
        2. color key - automatic conversion via attr.convert()
        3. default_value - if no color specified

        For segmented color attributes (segments > 1):
        1. raw_*_N key (e.g., raw_rgbw_0) - explicit per-segment
        2. color_N key (e.g., color_0) - per-segment with conversion
        3. color key - same color for all segments (with conversion)
        4. default_value - if no color specified
        """
        result: dict[int, int] = {}
        offset = 0
        for attr in self.attributes:
            segments = getattr(attr, "segments", 1)
            raw_name = getattr(attr, "raw_name", None)

            if segments > 1 and attr.name == "color":
                # Segmented color attribute - encode each segment
                base_channels = attr.channel_count // segments
                for seg in range(segments):
                    value = None
                    seg_raw_key = f"{raw_name}_{seg}" if raw_name else None
                    seg_key = f"color_{seg}"

                    # Check for segment-specific raw key
                    if seg_raw_key and seg_raw_key in state:
                        value = state[seg_raw_key]
                    # Check for segment-specific color key
                    elif seg_key in state:
                        color_value = state[seg_key]
                        if hasattr(attr, "convert"):
                            value = attr.convert(color_value)
                        else:
                            value = color_value
                    # Fall back to unified color key (same for all segments)
                    elif "color" in state:
                        color_value = state["color"]
                        if hasattr(attr, "convert"):
                            value = attr.convert(color_value)
                        else:
                            value = color_value
                    else:
                        value = attr.default_value

                    dmx_bytes = attr.encode(value)
                    for i, byte in enumerate(dmx_bytes[:base_channels]):
                        result[offset + i] = byte
                    offset += base_channels
            else:
                # Non-segmented attribute (original logic)
                value = None

                # Check for raw_* key first (bypass conversion)
                if raw_name and raw_name in state:
                    value = state[raw_name]
                # Check for color key with conversion
                elif attr.name == "color" and "color" in state:
                    color_value = state["color"]
                    if hasattr(attr, "convert"):
                        value = attr.convert(color_value)
                    else:
                        value = color_value
                # Fall back to attribute name or default
                elif attr.name in state:
                    value = state[attr.name]
                else:
                    value = attr.default_value

                dmx_bytes = attr.encode(value)
                for i, byte in enumerate(dmx_bytes):
                    result[offset + i] = byte
                offset += attr.channel_count
        return result


class FixtureContext:
    """Context manager that collects fixtures created within its scope."""

    def __init__(self) -> None:
        self.fixtures: list[Fixture] = []

    def __enter__(self) -> FixtureContext:
        return self

    def __exit__(self, *args: object) -> None:
        pass


@dataclass
class Fixture:
    """A single fixture in the rig."""

    fixture_type: FixtureType
    universe: int
    address: int
    pos: Vec3 = field(default_factory=Vec3)
    groups: set[FixtureGroup] = field(default_factory=set)
    meta: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Register this fixture with its groups."""
        for group in self.groups:
            group._add(self)

    @property
    def segment_count(self) -> int:
        """Max segments across all segmented attributes."""
        return max(
            (getattr(attr, "segments", 1) for attr in self.fixture_type.attributes),
            default=1,
        )

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Fixture):
            return NotImplemented
        return self is other


class Rig:
    """Collection of fixtures with lookup helpers."""

    def __init__(self, fixtures: list[Fixture] | None = None):
        self._fixtures: list[Fixture] = []
        for f in fixtures or []:
            self._check_overlap(f)
            self._fixtures.append(f)

    def _check_overlap(self, new_fixture: Fixture) -> None:
        """Raise ValueError if new_fixture overlaps with existing fixtures."""
        new_start = new_fixture.address
        new_end = new_fixture.address + new_fixture.fixture_type.channel_count - 1

        for existing in self._fixtures:
            if existing.universe != new_fixture.universe:
                continue
            existing_start = existing.address
            existing_end = existing.address + existing.fixture_type.channel_count - 1

            # Check for overlap: ranges overlap if one starts before the other ends
            if new_start <= existing_end and existing_start <= new_end:
                raise ValueError(
                    f"Fixture at universe {new_fixture.universe} address {new_fixture.address} "
                    f"(channels {new_start}-{new_end}) overlaps with existing fixture "
                    f"at address {existing.address} (channels {existing_start}-{existing_end})"
                )

    def add(self, fixture: Fixture) -> None:
        self._check_overlap(fixture)
        self._fixtures.append(fixture)

    @property
    def all(self) -> list[Fixture]:
        return list(self._fixtures)

    def encode_to_dmx(
        self, states: dict[Fixture, FixtureState]
    ) -> dict[int, dict[int, int]]:
        """Returns {universe_id: {channel: value}}"""
        universes: dict[int, dict[int, int]] = {}
        for fixture, state in states.items():
            universe_data = universes.setdefault(fixture.universe, {})
            channel_values = fixture.fixture_type.encode(state)
            for offset, value in channel_values.items():
                channel = fixture.address + offset
                if 1 <= channel <= 512:
                    universe_data[channel] = value
        return universes
