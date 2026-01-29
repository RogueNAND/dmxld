"""DMX engine with sACN and Art-Net support."""

from __future__ import annotations

import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

from dmxld.blend import FixtureDelta, merge_deltas
from dmxld.clips import Clip
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
    """sACN (E1.31) transport using sacn library."""

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
    """Art-Net transport using stupidArtnet library."""

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
    """DMX engine that plays clips via sACN or Art-Net."""

    rig: Rig | None = None
    protocol: Protocol = Protocol.SACN
    fps: float = 40.0
    universe_ips: dict[int, str] = field(default_factory=dict)
    artnet_target: str = "255.255.255.255"

    _running: bool = field(default=False, init=False, repr=False)
    _fixture_states: dict[Fixture, FixtureState] = field(
        default_factory=dict, init=False, repr=False
    )
    _transport: _Transport | None = field(default=None, init=False, repr=False)
    _timer: threading.Timer | None = field(default=None, init=False, repr=False)
    _done_event: threading.Event | None = field(default=None, init=False, repr=False)
    _current_clip: Clip | None = field(default=None, init=False, repr=False)
    _show_start: float = field(default=0.0, init=False, repr=False)
    _frame_duration: float = field(default=0.0, init=False, repr=False)

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

    def _apply_deltas(self, deltas: dict[Fixture, FixtureDelta]) -> None:
        if self.rig is None:
            return
        for fixture in self.rig.all:
            if fixture in deltas:
                self._fixture_states[fixture] = merge_deltas(
                    [deltas[fixture]], self._fixture_states[fixture]
                )

    def play(self, clip: Clip, start_at: float = 0.0) -> None:
        """Non-blocking playback."""
        if self.rig is None:
            raise ValueError("No rig configured")

        self._transport = self._create_transport()
        self._transport.start()

        self._running = True
        self._frame_duration = 1.0 / self.fps
        self._show_start = time.monotonic() - start_at
        self._current_clip = clip
        self._done_event = threading.Event()

        self._init_fixture_states()
        self._schedule_frame()

    def _schedule_frame(self) -> None:
        if not self._running:
            self._finish_playback()
            return

        show_time = time.monotonic() - self._show_start

        if (
            self._current_clip is not None
            and self._current_clip.duration is not None
            and show_time > self._current_clip.duration
        ):
            self._finish_playback()
            return

        if self._current_clip is not None and self.rig is not None:
            deltas = self._current_clip.render(show_time, self.rig)
            self._apply_deltas(deltas)
            universe_data = self.rig.encode_to_dmx(self._fixture_states)
            if self._transport is not None:
                self._transport.send(universe_data)

        self._timer = threading.Timer(self._frame_duration, self._schedule_frame)
        self._timer.daemon = True
        self._timer.start()

    def _finish_playback(self) -> None:
        self._running = False
        if self._transport is not None:
            self._transport.stop()
            self._transport = None
        if self._done_event is not None:
            self._done_event.set()

    def stop(self) -> None:
        self._running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def wait(self) -> None:
        """Block until playback completes."""
        if self._done_event is not None:
            self._done_event.wait()

    def play_sync(self, clip: Clip, start_at: float = 0.0) -> None:
        self.play(clip, start_at)
        try:
            self.wait()
        except KeyboardInterrupt:
            self.stop()

    def render_frame(self, clip: Clip, t: float) -> dict[int, dict[int, int]]:
        """For testing without network."""
        if self.rig is None:
            return {}

        for fixture in self.rig.all:
            self._fixture_states[fixture] = FixtureState()

        deltas = clip.render(t, self.rig)
        self._apply_deltas(deltas)

        return self.rig.encode_to_dmx(self._fixture_states)
