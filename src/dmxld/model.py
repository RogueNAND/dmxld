"""Data model layer for dmxld."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


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

    def __init__(self, *attributes: Attribute) -> None:
        self.attributes = attributes
        self.channel_count = sum(attr.channel_count for attr in attributes)

    def encode(self, state: FixtureState) -> dict[int, int]:
        """Encode state to DMX values (0-255)."""
        result: dict[int, int] = {}
        offset = 0
        for attr in self.attributes:
            value = state.get(attr.name, attr.default_value)
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
    tags: set[str] = field(default_factory=set)
    meta: dict[str, object] = field(default_factory=dict)

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
        self._by_tag: dict[str, list[Fixture]] = {}
        for f in fixtures or []:
            self._check_overlap(f)
            self._fixtures.append(f)
        self._rebuild_indices()

    def _rebuild_indices(self) -> None:
        self._by_tag.clear()
        for f in self._fixtures:
            for tag in f.tags:
                self._by_tag.setdefault(tag, []).append(f)

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
