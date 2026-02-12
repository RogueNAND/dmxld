"""DMX engine with sACN and Art-Net support."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from dmxld.blend import FixtureDelta, merge_deltas
from dmxld.clips import Clip, Scene
from dmxld.model import Fixture, FixtureState, Rig

if TYPE_CHECKING:
    import sacn
    from stupidArtnet import StupidArtnet


class Protocol(Enum):
    """DMX-over-IP protocol selection."""

    SACN = "sacn"
    ARTNET = "artnet"


class _Transport(ABC):
    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def send(self, universe_data: dict[int, dict[int, int]]) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...


class _SACNTransport(_Transport):
    def __init__(
        self,
        universes: list[int],
        universe_ips: dict[int, str],
        fps: float,
    ) -> None:
        import sacn

        self._sender = sacn.sACNsender(fps=int(fps))
        self._universes = universes
        self._universe_ips = universe_ips

    def start(self) -> None:
        self._sender.start()
        for u in self._universes:
            self._sender.activate_output(u)
            if u in self._universe_ips:
                self._sender[u].destination = self._universe_ips[u]
            else:
                self._sender[u].multicast = True

    def send(self, universe_data: dict[int, dict[int, int]]) -> None:
        for u in self._universes:
            data = universe_data.get(u, {})
            dmx = tuple(data.get(ch, 0) for ch in range(1, 513))
            self._sender[u].dmx_data = dmx

    def stop(self) -> None:
        self._sender.stop()


class _ArtNetTransport(_Transport):
    def __init__(
        self,
        universes: list[int],
        universe_ips: dict[int, str],
        default_target: str,
        fps: float,
    ) -> None:
        from stupidArtnet import StupidArtnet

        self._senders: dict[int, StupidArtnet] = {}
        for u in universes:
            target = universe_ips.get(u, default_target)
            is_broadcast = target in ("255.255.255.255", "<broadcast>")
            self._senders[u] = StupidArtnet(
                target, u, 512, int(fps), broadcast=is_broadcast
            )

    def start(self) -> None:
        for sender in self._senders.values():
            sender.start()

    def send(self, universe_data: dict[int, dict[int, int]]) -> None:
        for u, sender in self._senders.items():
            data = universe_data.get(u, {})
            packet = bytearray(512)
            for ch, val in data.items():
                if 1 <= ch <= 512:
                    packet[ch - 1] = val
            sender.set(packet)

    def stop(self) -> None:
        for sender in self._senders.values():
            sender.stop()


@dataclass
class DMXEngine:
    """DMX engine that renders clips and sends DMX via sACN or Art-Net."""

    rig: Rig | None = None
    protocol: Protocol = Protocol.SACN
    fps: float = 40.0
    universe_ips: dict[int, str] = field(default_factory=dict)
    artnet_target: str = "255.255.255.255"

    _fixture_states: dict[Fixture, FixtureState] = field(default_factory=dict, init=False, repr=False)
    _transport: _Transport | None = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        if self.rig is not None:
            self._init_fixture_states()

    def _init_fixture_states(self) -> None:
        self._fixture_states.clear()
        if self.rig is not None:
            for fixture in self.rig.all:
                self._fixture_states[fixture] = FixtureState()

    def set_rig(self, rig: Rig) -> None:
        self.rig = rig
        self._init_fixture_states()

    def _get_universes(self) -> list[int]:
        if self.rig is None:
            return [1]
        universes = set()
        for fixture in self.rig.all:
            universes.add(fixture.universe)
        return sorted(universes) if universes else [1]

    def _create_transport(self) -> _Transport:
        universes = self._get_universes()
        if self.protocol == Protocol.SACN:
            return _SACNTransport(universes, self.universe_ips, self.fps)
        else:
            return _ArtNetTransport(
                universes, self.universe_ips, self.artnet_target, self.fps
            )

    def apply_deltas(
        self, deltas: dict[Fixture, FixtureDelta]
    ) -> dict[int, dict[int, int]]:
        """Apply deltas to fixture states and encode to DMX."""
        if self.rig is None:
            return {}
        for fixture in self.rig.all:
            if fixture in deltas:
                self._fixture_states[fixture] = merge_deltas(
                    [deltas[fixture]], self._fixture_states[fixture]
                )
        return self.rig.encode_to_dmx(self._fixture_states)

    def start(self) -> None:
        """Start the DMX transport (sACN or Art-Net)."""
        if self._transport is None:
            self._transport = self._create_transport()
            self._transport.start()

    def stop(self) -> None:
        """Stop the DMX transport."""
        if self._transport is not None:
            self._transport.stop()
            self._transport = None

    def send(self, universe_data: dict[int, dict[int, int]]) -> None:
        """Send DMX data to the transport."""
        if self._transport is not None:
            self._transport.send(universe_data)

    def render_frame(self, clip: Clip, t: float) -> dict[int, dict[int, int]]:
        if self.rig is None:
            return {}
        self._init_fixture_states()
        deltas = clip.render(t, self.rig)
        return self.apply_deltas(deltas)

    def render_deltas(self, deltas: dict[Fixture, FixtureDelta]) -> dict[int, dict[int, int]]:
        """Reset fixture states, apply deltas, encode to DMX. Use as Runner apply_fn."""
        if self.rig is None:
            return {}
        self._init_fixture_states()
        return self.apply_deltas(deltas)

    def render_scene(self, scene: Scene) -> dict[int, dict[int, int]]:
        """Render a Scene to DMX data (no time parameter)."""
        if self.rig is None:
            return {}
        self._init_fixture_states()
        deltas = scene.render(self.rig)
        return self.apply_deltas(deltas)

    def show(self, scene: Scene) -> None:
        """Render a scene and immediately send it."""
        self.send(self.render_scene(scene))
