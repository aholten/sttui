"""Single-instance lock for stttui.

A second invocation must fail fast because two processes cannot share the
global record hotkey, the audio input device, or the transcription log.
"""

from __future__ import annotations

import atexit
import errno
import os
import signal
import sys
from pathlib import Path

LOCK_DIR = Path.home() / ".stttui"
LOCK_FILE = LOCK_DIR / "stttui.lock"


class AlreadyRunningError(RuntimeError):
    def __init__(self, pid: int):
        super().__init__(f"stttui is already running (PID {pid})")
        self.pid = pid


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # Process exists but is owned by another user — treat as alive.
        return True
    except OSError as e:
        # Windows: EPERM → alive, ESRCH → dead. Other errors: conservative "alive".
        if e.errno == errno.ESRCH:
            return False
        return True
    return True


def _read_pid(path: Path) -> int:
    try:
        return int(path.read_text().strip())
    except (OSError, ValueError):
        return 0


def _release_lock() -> None:
    try:
        if LOCK_FILE.exists() and _read_pid(LOCK_FILE) == os.getpid():
            LOCK_FILE.unlink()
    except OSError:
        pass


def acquire_singleton_lock() -> Path:
    """Claim the singleton lock or raise AlreadyRunningError.

    Uses atomic O_CREAT|O_EXCL to avoid a TOCTOU race between two launches
    starting near-simultaneously. A stale lock (owning PID gone) is recovered
    by unlinking and retrying once.
    """
    LOCK_DIR.mkdir(parents=True, exist_ok=True)

    for attempt in range(2):
        try:
            fd = os.open(
                LOCK_FILE,
                os.O_CREAT | os.O_EXCL | os.O_WRONLY,
                0o644,
            )
        except FileExistsError:
            pid = _read_pid(LOCK_FILE)
            if _pid_alive(pid):
                raise AlreadyRunningError(pid)
            # Stale — remove and try again.
            try:
                LOCK_FILE.unlink()
            except FileNotFoundError:
                pass
            continue

        try:
            os.write(fd, f"{os.getpid()}\n".encode())
            os.fsync(fd)
        finally:
            os.close(fd)

        atexit.register(_release_lock)
        _install_signal_handlers()
        return LOCK_FILE

    # Shouldn't happen — second iteration either succeeds or raises.
    raise AlreadyRunningError(_read_pid(LOCK_FILE))


def _install_signal_handlers() -> None:
    """Release the lock on SIGTERM/SIGHUP so `kill <pid>` doesn't strand it."""
    def handler(signum, _frame):
        _release_lock()
        # Restore default and re-raise so the process exits normally.
        signal.signal(signum, signal.SIG_DFL)
        os.kill(os.getpid(), signum)

    for sig_name in ("SIGTERM", "SIGHUP"):
        sig = getattr(signal, sig_name, None)
        if sig is None:
            continue
        try:
            signal.signal(sig, handler)
        except (ValueError, OSError):
            # Not main thread, or signal not supported on this platform.
            pass
