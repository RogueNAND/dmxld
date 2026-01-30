"""Generic frame loop runner for timeline playback."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from typing import Callable, Generic, TypeVar

from timeline.clip import Clip

Ctx = TypeVar("Ctx")
Target = TypeVar("Target")
Delta = TypeVar("Delta")
Output = TypeVar("Output")


@dataclass
class Runner(Generic[Ctx, Target, Delta, Output]):
    """Frame loop runner."""

    ctx: Ctx
    apply_fn: Callable[[dict[Target, Delta]], Output]
    output_fn: Callable[[Output], None] | None = None
    fps: float = 40.0

    _running: bool = field(default=False, init=False, repr=False)
    _timer: threading.Timer | None = field(default=None, init=False, repr=False)
    _done_event: threading.Event | None = field(default=None, init=False, repr=False)
    _current_clip: Clip[Ctx, Target, Delta] | None = field(
        default=None, init=False, repr=False
    )
    _start_time: float = field(default=0.0, init=False, repr=False)
    _frame_duration: float = field(default=0.0, init=False, repr=False)

    def play(self, clip: Clip[Ctx, Target, Delta], start_at: float = 0.0) -> None:
        self._running = True
        self._frame_duration = 1.0 / self.fps
        self._start_time = time.monotonic() - start_at
        self._current_clip = clip
        self._done_event = threading.Event()
        self._schedule_frame()

    def _schedule_frame(self) -> None:
        if not self._running:
            self._finish_playback()
            return

        show_time = time.monotonic() - self._start_time

        if (
            self._current_clip is not None
            and self._current_clip.duration is not None
            and show_time > self._current_clip.duration
        ):
            self._finish_playback()
            return

        if self._current_clip is not None:
            deltas = self._current_clip.render(show_time, self.ctx)
            output = self.apply_fn(deltas)
            if self.output_fn is not None:
                self.output_fn(output)

        self._timer = threading.Timer(self._frame_duration, self._schedule_frame)
        self._timer.daemon = True
        self._timer.start()

    def _finish_playback(self) -> None:
        self._running = False
        if self._done_event is not None:
            self._done_event.set()

    def stop(self) -> None:
        self._running = False
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def wait(self) -> None:
        if self._done_event is not None:
            self._done_event.wait()

    def play_sync(self, clip: Clip[Ctx, Target, Delta], start_at: float = 0.0) -> None:
        self.play(clip, start_at)
        try:
            self.wait()
        except KeyboardInterrupt:
            self.stop()

    def render_frame(self, clip: Clip[Ctx, Target, Delta], t: float) -> Output:
        deltas = clip.render(t, self.ctx)
        return self.apply_fn(deltas)
