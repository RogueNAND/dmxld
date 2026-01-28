"""Data model layer for olald."""

from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True)
class Vec3:
    """3D position vector."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class FixtureState:
    """Current state of a fixture."""

    dimmer: float = 0.0
    rgb: tuple[float, float, float] = (0.0, 0.0, 0.0)

    def copy(self) -> FixtureState:
        return FixtureState(dimmer=self.dimmer, rgb=self.rgb)


@runtime_checkable
class FixtureType(Protocol):
    """Protocol for fixture type definitions."""

    @property
    def name(self) -> str: ...

    @property
    def channel_count(self) -> int: ...

    def encode(self, state: FixtureState) -> dict[int, int]:
        """Encode state to DMX channel values (0-255). Keys are channel offsets."""
        ...


class GenericRGBDimmer:
    """Generic RGBD fixture: 4 channels (dimmer, R, G, B)."""

    @property
    def name(self) -> str:
        return "GenericRGBDimmer"

    @property
    def channel_count(self) -> int:
        return 4

    def encode(self, state: FixtureState) -> dict[int, int]:
        """Encode state to DMX values. Channel offsets: 0=dimmer, 1=R, 2=G, 3=B."""

        def to_dmx(v: float) -> int:
            return max(0, min(255, int(v * 255)))

        return {
            0: to_dmx(state.dimmer),
            1: to_dmx(state.rgb[0]),
            2: to_dmx(state.rgb[1]),
            3: to_dmx(state.rgb[2]),
        }


_fixture_registry: ContextVar[list[Fixture] | None] = ContextVar(
    "_fixture_registry", default=None
)


def _register_fixture(fixture: Fixture) -> None:
    """Register a fixture with the current context if one exists."""
    registry = _fixture_registry.get()
    if registry is not None:
        registry.append(fixture)


class FixtureContext:
    """Context manager that collects fixtures created within its scope."""

    def __init__(self) -> None:
        self._fixtures: list[Fixture] = []
        self._token: object = None

    def __enter__(self) -> FixtureContext:
        self._fixtures = []
        self._token = _fixture_registry.set(self._fixtures)
        return self

    def __exit__(self, *args: object) -> None:
        _fixture_registry.reset(self._token)

    @property
    def fixtures(self) -> list[Fixture]:
        """Return collected fixtures."""
        return list(self._fixtures)


@dataclass
class Fixture:
    """A single fixture in the rig."""

    fixture_type: FixtureType
    universe: int
    address: int
    pos: Vec3 = field(default_factory=Vec3)
    tags: set[str] = field(default_factory=set)
    meta: dict[str, object] = field(default_factory=dict)

    def __post_init__(self) -> None:
        _register_fixture(self)

    def __hash__(self) -> int:
        return id(self)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Fixture):
            return NotImplemented
        return self is other


class Rig:
    """Collection of fixtures with lookup helpers."""

    def __init__(self, fixtures: list[Fixture] | None = None):
        self._fixtures: list[Fixture] = fixtures or []
        self._by_tag: dict[str, list[Fixture]] = {}
        self._rebuild_indices()

    def _rebuild_indices(self) -> None:
        self._by_tag.clear()
        for f in self._fixtures:
            for tag in f.tags:
                self._by_tag.setdefault(tag, []).append(f)

    def add(self, fixture: Fixture) -> None:
        self._fixtures.append(fixture)
        for tag in fixture.tags:
            self._by_tag.setdefault(tag, []).append(fixture)

    @property
    def all(self) -> list[Fixture]:
        return list(self._fixtures)

    def by_tag(self, tag: str) -> list[Fixture]:
        return list(self._by_tag.get(tag, []))

    def encode_to_dmx(
        self, states: dict[Fixture, FixtureState]
    ) -> dict[int, dict[int, int]]:
        """Encode fixture states to DMX data per universe.

        Returns: {universe_id: {channel: value}}
        """
        universes: dict[int, dict[int, int]] = {}
        for fixture, state in states.items():
            universe_data = universes.setdefault(fixture.universe, {})
            channel_values = fixture.fixture_type.encode(state)
            for offset, value in channel_values.items():
                channel = fixture.address + offset
                if 1 <= channel <= 512:
                    universe_data[channel] = value
        return universes
