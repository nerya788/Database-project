"""Thread-safe bridge from background work to Tkinter callbacks.

Python 3.13+ hardened tkinter's threading rules: only the main thread, while
it is actually inside the Tk event loop, may call into the Tcl interpreter
(register commands, schedule timers, etc). A worker thread calling
`widget.after(...)` itself now raises `RuntimeError: main thread is not in
main loop` - and it can happen even for work started from a constructor,
before `mainloop()` has been entered, if the worker finishes fast enough to
win the race.

The fix: workers never touch Tk at all. They drop their result on a plain
`queue.Queue` (thread-safe by design). A single dispatcher loop - started
once, from the main thread, via `start_dispatcher()` - polls that queue on
every Tk event-loop tick (scheduled with the widget's own `.after()`, always
called from the main thread) and invokes the callback there. Because the
queue just buffers pending results until the dispatcher starts ticking, it
is fully safe to start background work from a constructor even before
`mainloop()` has been called.
"""
from __future__ import annotations

import queue
import threading
import tkinter as tk
from typing import Callable

_POLL_MS = 50
_task_queue: "queue.Queue[tuple[tk.Misc, Callable[[object], None], object]]" = queue.Queue()
_dispatcher_root: tk.Misc | None = None


def start_dispatcher(root: tk.Misc) -> None:
    """Start the queue-draining loop. Call once, from the main thread,
    before (or right at the start of) `root.mainloop()`. Safe to call more
    than once - later calls are ignored.
    """
    global _dispatcher_root
    if _dispatcher_root is not None:
        return
    _dispatcher_root = root
    root.after(_POLL_MS, _drain_queue)


def _drain_queue() -> None:
    while True:
        try:
            widget, callback, payload = _task_queue.get_nowait()
        except queue.Empty:
            break
        try:
            if widget.winfo_exists():
                callback(payload)
        except tk.TclError:
            pass  # widget was destroyed between being queued and being drained

    try:
        if _dispatcher_root.winfo_exists():
            _dispatcher_root.after(_POLL_MS, _drain_queue)
    except tk.TclError:
        pass  # root window has been destroyed - stop rescheduling


def run_in_background(
    widget: tk.Misc,
    work: Callable[[], object],
    on_success: Callable[[object], None],
    on_error: Callable[[Exception], None],
) -> None:
    """Run `work()` off the UI thread. Its result/exception is delivered to
    `on_success` / `on_error` on the main thread, via the dispatcher queue -
    never by the worker thread calling into Tk directly.
    """
    if _dispatcher_root is None:
        raise RuntimeError(
            "async_utils.start_dispatcher(root) must be called once, from the "
            "main thread, before any run_in_background() call."
        )

    def worker() -> None:
        try:
            result = work()
        except Exception as exc:  # noqa: BLE001 - forwarded to on_error
            _task_queue.put((widget, on_error, exc))
        else:
            _task_queue.put((widget, on_success, result))

    threading.Thread(target=worker, daemon=True).start()
