"""DMX engine using OLA ClientWrapper."""

from __future__ import annotations

import array
import os
import socket
import time
from dataclasses import dataclass, field

from fcld.blend import merge_deltas
from fcld.clips import Clip
from fcld.model import Fixture, FixtureState, Rig

try:
    from ola.ClientWrapper import ClientWrapper
    from ola.OlaClient import OlaClient

    OLA_AVAILABLE = True
except ImportError:
    OLA_AVAILABLE = False
    ClientWrapper = None
    OlaClient = None


class DMXArray(array.array):
    """Array subclass with tostring() for OLA compatibility."""

    def __new__(cls, data: list[int]) -> "DMXArray":
        return super().__new__(cls, "B", data)

    def tostring(self) -> bytes:
        """Return bytes (OLA library compatibility)."""
        return self.tobytes()


@dataclass
class DMXEngine:
    """DMX engine that plays clips through OLA."""

    rig: Rig
    universe_ids: list[int] = field(default_factory=lambda: [1])
    fps: float = 40.0

    _running: bool = field(default=False, init=False)
    _fixture_states: dict[Fixture, FixtureState] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        for fixture in self.rig.all:
            self._fixture_states[fixture] = FixtureState()

    def _apply_deltas(self, deltas: dict[Fixture, object]) -> None:
        """Apply deltas to tracked fixture states."""
        for fixture in self.rig.all:
            if fixture in deltas:
                self._fixture_states[fixture] = merge_deltas(
                    [deltas[fixture]], self._fixture_states[fixture]
                )

    def _send_dmx(self, client: object, universe_data: dict[int, dict[int, int]]) -> None:
        """Send DMX data to OLA."""
        for universe_id in self.universe_ids:
            data = universe_data.get(universe_id, {})
            dmx_array = [0] * 512
            for channel, value in data.items():
                if 1 <= channel <= 512:
                    dmx_array[channel - 1] = value
            if OLA_AVAILABLE and client is not None:
                client.SendDmx(universe_id, DMXArray(dmx_array))

    def play(self, clip: Clip, start_at: float = 0.0) -> None:
        """Play a clip from the given start time."""
        if not OLA_AVAILABLE:
            print("ERROR: OLA Python module not available.")
            print("Install with: pip install ola")
            return

        ola_host = os.environ.get("OLA_HOST")
        ola_port = os.environ.get("OLA_PORT", "9010")

        if ola_host:
            print(f"Connecting to OLA at {ola_host}:{ola_port}")
            self._play_remote(clip, start_at, ola_host, int(ola_port))
        else:
            print("Connecting to local OLA")
            self._play_local(clip, start_at)

    def _play_local(self, clip: Clip, start_at: float) -> None:
        """Play using local ClientWrapper (event-driven)."""
        self._running = True
        wrapper = ClientWrapper()
        client = wrapper.Client()

        frame_duration = 1.0 / self.fps
        show_start = time.monotonic() - start_at

        def tick() -> None:
            if not self._running:
                wrapper.Stop()
                return

            show_time = time.monotonic() - show_start

            if clip.duration is not None and show_time > clip.duration:
                self._running = False
                wrapper.Stop()
                return

            deltas = clip.render(show_time, self.rig)
            self._apply_deltas(deltas)

            universe_data = self.rig.encode_to_dmx(self._fixture_states)
            self._send_dmx(client, universe_data)

            wrapper.AddEvent(int(frame_duration * 1000), tick)

        wrapper.AddEvent(0, tick)

        try:
            wrapper.Run()
        except KeyboardInterrupt:
            self._running = False

    def _play_remote(self, clip: Clip, start_at: float, host: str, port: int) -> None:
        """Play using remote OLA connection (polling loop)."""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((host, port))
        client = OlaClient(sock)

        self._running = True
        frame_duration = 1.0 / self.fps
        show_start = time.monotonic() - start_at

        try:
            while self._running:
                frame_start = time.monotonic()
                show_time = frame_start - show_start

                if clip.duration is not None and show_time > clip.duration:
                    break

                deltas = clip.render(show_time, self.rig)
                self._apply_deltas(deltas)

                universe_data = self.rig.encode_to_dmx(self._fixture_states)
                self._send_dmx(client, universe_data)

                elapsed = time.monotonic() - frame_start
                sleep_time = frame_duration - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
        except KeyboardInterrupt:
            pass
        finally:
            sock.close()

    def stop(self) -> None:
        """Signal the engine to stop."""
        self._running = False

    def render_frame(self, clip: Clip, t: float) -> dict[int, dict[int, int]]:
        """Render a single frame without OLA (for testing)."""
        for fixture in self.rig.all:
            self._fixture_states[fixture] = FixtureState()

        deltas = clip.render(t, self.rig)
        self._apply_deltas(deltas)

        return self.rig.encode_to_dmx(self._fixture_states)
