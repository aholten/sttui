"""
sttui — Speech-to-Text TUI

Press Ctrl+Shift+Space to start recording.
Press Ctrl+Shift+Space again to stop recording, transcribe, and paste.
Press Ctrl+C to quit.

Run with --cli for CLI-only mode.
"""

import argparse
import os
import signal
import sys
import tempfile
import threading
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

if sys.version_info < (3, 10):
    sys.exit("sttui requires Python 3.10 or later.")

import numpy as np
import pyperclip
import sounddevice as sd
import soundfile as sf
from faster_whisper import WhisperModel
from pynput import keyboard as pynput_keyboard

_SCRIPT_DIR = Path(__file__).resolve().parent
VERSION = (_SCRIPT_DIR / "VERSION").read_text().strip()

HOTKEY_RECORD = "ctrl+shift+space"
HOTKEY_QUIT = "ctrl+c"
SAMPLE_RATE = 16000
CHANNELS = 1
LOG_FILE = _SCRIPT_DIR / "transcription_log.txt"
EASTERN = ZoneInfo("America/New_York")
MODEL_SIZES = ["tiny", "base", "small", "medium", "large"]

# RMS level throttle
_LEVEL_INTERVAL = 1.0 / 15  # ~15 updates/sec


class SpeechToText:
    """Core engine with callback hooks for UI integration."""

    def __init__(self, model_name="base"):
        self.recording = False
        self.audio_chunks = []
        self.stream = None
        self.model = None
        self.model_name = model_name
        self.lock = threading.Lock()
        self._last_level_time = 0.0

        # Callback hooks — default to print for CLI mode
        self.on_status = lambda msg: print(msg)
        self.on_transcription = lambda text, ts: print(f"Transcription: {text}")
        self.on_level = lambda rms: None
        self.on_state_change = lambda state: None

    def load_model(self):
        self.on_status(f"Loading faster-whisper model '{self.model_name}' (CPU, int8)...")
        self.model = WhisperModel(
            self.model_name, device="cpu", compute_type="int8"
        )
        self.on_status("Model loaded. Ready!")

    def audio_callback(self, indata, frames, time_info, status):
        if status:
            self.on_status(f"Audio status: {status}")
        self.audio_chunks.append(indata.copy())

        # Throttled RMS level
        now = time.monotonic()
        if now - self._last_level_time >= _LEVEL_INTERVAL:
            self._last_level_time = now
            rms = float(np.sqrt(np.mean(indata ** 2)))
            self.on_level(rms)

    def start_recording(self):
        self.audio_chunks = []
        self.stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype="float32",
            callback=self.audio_callback,
        )
        self.stream.start()
        self.recording = True
        self.on_state_change("RECORDING")
        self.on_status(f"Recording... (press {HOTKEY_RECORD} again to stop)")

    def stop_recording(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.recording = False
        self.on_state_change("TRANSCRIBING")
        self.on_status("Recording stopped. Transcribing...")

    def transcribe(self):
        if not self.audio_chunks:
            self.on_status("No audio recorded.")
            self.on_state_change("IDLE")
            return

        audio = np.concatenate(self.audio_chunks, axis=0).flatten()
        duration = len(audio) / SAMPLE_RATE
        self.on_status(f"Audio duration: {duration:.1f}s")

        if duration < 0.5:
            self.on_status("Too short, skipping.")
            self.on_state_change("IDLE")
            return

        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()

        try:
            sf.write(tmp_path, audio, SAMPLE_RATE)
            segments, info = self.model.transcribe(tmp_path)
            text = " ".join(seg.text.strip() for seg in segments).strip()

            if text:
                pyperclip.copy(text)
                timestamp = datetime.now(EASTERN).strftime("%Y-%m-%d %I:%M:%S %p %Z")
                self.on_transcription(text, timestamp)
                self._log_transcription(text, timestamp)
            else:
                self.on_status("No speech detected.")
        finally:
            os.unlink(tmp_path)
            self.on_state_change("IDLE")

    def _log_transcription(self, text, timestamp=None):
        if timestamp is None:
            timestamp = datetime.now(EASTERN).strftime("%Y-%m-%d %I:%M:%S %p %Z")
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(f"[{timestamp}] {text}\n")

    def toggle_recording(self):
        with self.lock:
            if not self.recording:
                self.start_recording()
            else:
                self.stop_recording()
                self.transcribe()


# ---------------------------------------------------------------------------
# Cross-platform hotkey handling (pynput)
# ---------------------------------------------------------------------------

# Canonical key names used in the pressed set
_KEY_CTRL = "ctrl"
_KEY_SHIFT = "shift"
_KEY_SPACE = "space"

_RECORD_COMBO = frozenset({_KEY_CTRL, _KEY_SHIFT, _KEY_SPACE})


def _normalise_key(key):
    """Map any pynput key to a canonical string for reliable matching."""
    # Modifier keys
    if key in (pynput_keyboard.Key.shift, pynput_keyboard.Key.shift_l, pynput_keyboard.Key.shift_r):
        return _KEY_SHIFT
    if key in (pynput_keyboard.Key.ctrl, pynput_keyboard.Key.ctrl_l, pynput_keyboard.Key.ctrl_r):
        return _KEY_CTRL
    # Space — can arrive as Key.space, KeyCode(char=' '), or KeyCode(vk=32, char=None)
    if key == pynput_keyboard.Key.space:
        return _KEY_SPACE
    if isinstance(key, pynput_keyboard.KeyCode):
        if key.char == ' ':
            return _KEY_SPACE
        if getattr(key, 'vk', None) == 32:
            return _KEY_SPACE
        if key.char:
            return key.char.lower()
    return key


def _create_hotkey_listener(on_record):
    """Create a pynput keyboard listener for the record hotkey.

    The listener never suppresses keys — all other shortcuts continue to work
    normally while recording. Includes a 300ms debounce to prevent double-fires.
    """
    pressed = set()
    last_fire = [0.0]

    def on_press(key):
        pressed.add(_normalise_key(key))
        if _RECORD_COMBO.issubset(pressed):
            now = time.monotonic()
            if now - last_fire[0] < 0.3:
                return
            last_fire[0] = now
            threading.Thread(target=on_record, daemon=True).start()

    def on_release(key):
        pressed.discard(_normalise_key(key))

    return pynput_keyboard.Listener(on_press=on_press, on_release=on_release, suppress=False)


# ---------------------------------------------------------------------------
# CLI mode (original behavior)
# ---------------------------------------------------------------------------

def run_cli(model_name="base"):
    stt = SpeechToText(model_name=model_name)

    def cli_transcription(text, ts):
        print(f"Transcription: {text}")
        print("Copied to clipboard! Use Ctrl+V to paste.")

    stt.on_transcription = cli_transcription

    stt.load_model()
    print(f"  Press {HOTKEY_RECORD} to start/stop recording")
    print(f"  Press {HOTKEY_QUIT} to quit")
    print("\nListening for hotkey...")

    signal.signal(signal.SIGINT, lambda *_: os._exit(0))

    listener = _create_hotkey_listener(on_record=stt.toggle_recording)
    listener.start()
    listener.join()


# ---------------------------------------------------------------------------
# TUI mode (Textual)
# ---------------------------------------------------------------------------

def run_tui(model_name="base"):
    from textual.app import App, ComposeResult
    from textual.binding import Binding
    from textual.containers import Horizontal, Vertical
    from textual.reactive import reactive
    from textual.widgets import Footer, Header, ProgressBar, RichLog, Select, Static

    APP_CSS = """
    #top-bar {
        height: 3;
        padding: 0 1;
    }

    #model-select {
        width: 24;
    }

    #status-badge {
        width: 20;
        content-align: center middle;
        text-style: bold;
        margin-left: 2;
        padding: 0 1;
    }

    #status-badge.idle {
        background: $primary-darken-2;
        color: $text;
    }

    #status-badge.recording {
        background: $error;
        color: $text;
    }

    #status-badge.transcribing {
        background: $warning;
        color: $text;
    }

    #main-content {
        height: 1fr;
    }

    #level-meter {
        height: 1;
        margin: 0 1;
    }

    #transcription-history {
        height: 1fr;
        margin: 0 1;
        border: solid $primary;
    }

    #status-log {
        height: 7;
        margin: 0 1;
        border: solid $accent;
    }
    """

    class SpeechToTextApp(App):
        TITLE = "sttui"
        CSS = APP_CSS

        BINDINGS = [
            Binding("ctrl+shift+space", "toggle_record_binding", "Record", show=True),
            Binding("ctrl+c", "quit_app", "Quit", show=True, priority=True),
        ]

        state = reactive("IDLE")

        def __init__(self, initial_model: str = "base"):
            super().__init__()
            self.engine = SpeechToText(model_name=initial_model)
            self._initial_model = initial_model
            self._listener = None
            # Threading event for cross-thread signalling
            self._toggle_event = threading.Event()
            self._last_toggle_time = 0.0
            # Queues for engine callbacks → UI
            self._status_queue = []
            self._transcription_queue = []
            self._level_value = 0.0
            self._pending_state = None
            self._queue_lock = threading.Lock()

        def compose(self) -> ComposeResult:
            yield Header()
            with Horizontal(id="top-bar"):
                yield Select(
                    [(s, s) for s in MODEL_SIZES],
                    value=self._initial_model,
                    id="model-select",
                    allow_blank=False,
                )
                yield Static("IDLE", id="status-badge", classes="idle")
            with Vertical(id="main-content"):
                yield ProgressBar(id="level-meter", total=100, show_eta=False, show_percentage=False)
                yield RichLog(id="transcription-history", highlight=True, markup=True)
            yield RichLog(id="status-log", highlight=True, markup=True, max_lines=50)
            yield Footer()

        def on_mount(self) -> None:
            # Wire engine callbacks to queue updates (thread-safe)
            self.engine.on_status = self._enqueue_status
            self.engine.on_transcription = self._enqueue_transcription
            self.engine.on_level = self._enqueue_level
            self.engine.on_state_change = self._enqueue_state

            # Register global record hotkey via pynput
            self._listener = _create_hotkey_listener(
                on_record=self._toggle_event.set,
            )
            self._listener.start()

            # Poll events and queues from Textual's own timer (~20 Hz)
            self.set_interval(0.05, self._poll)

            # Load model in background
            self.run_worker(self._load_model_worker, thread=True)

        async def _load_model_worker(self) -> None:
            self.engine.load_model()

        # -- Thread-safe enqueue helpers (called from engine/audio threads) --

        def _enqueue_status(self, msg: str) -> None:
            with self._queue_lock:
                self._status_queue.append(msg)

        def _enqueue_transcription(self, text: str, ts: str) -> None:
            with self._queue_lock:
                self._transcription_queue.append((text, ts))

        def _enqueue_level(self, rms: float) -> None:
            self._level_value = rms

        def _enqueue_state(self, s: str) -> None:
            self._pending_state = s

        # -- Polling (runs on Textual main thread via set_interval) --

        def _poll(self) -> None:
            # Check hotkey events
            if self._toggle_event.is_set():
                self._toggle_event.clear()
                self._toggle_record()

            # Drain queued UI updates
            with self._queue_lock:
                statuses = self._status_queue[:]
                self._status_queue.clear()
                transcriptions = self._transcription_queue[:]
                self._transcription_queue.clear()

            for msg in statuses:
                self._log_status(msg)
            for text, ts in transcriptions:
                self._add_transcription(text, ts)

            # Update level meter
            rms = self._level_value
            level = min(100, int(rms * 700))
            bar = self.query_one("#level-meter", ProgressBar)
            bar.update(progress=level)

            # Update state
            pending = self._pending_state
            if pending is not None:
                self._pending_state = None
                self.state = pending

        # -- State management --

        def watch_state(self, new_state: str) -> None:
            badge = self.query_one("#status-badge", Static)
            badge.update(new_state)
            badge.remove_class("idle", "recording", "transcribing")
            badge.add_class(new_state.lower())

            if new_state != "RECORDING":
                level = self.query_one("#level-meter", ProgressBar)
                level.update(progress=0)

        # -- UI helpers --

        def _log_status(self, msg: str) -> None:
            log = self.query_one("#status-log", RichLog)
            log.write(msg)

        def _add_transcription(self, text: str, timestamp: str) -> None:
            history = self.query_one("#transcription-history", RichLog)
            history.write(f"[dim]{timestamp}[/dim]  {text}")
            self._log_status("Copied to clipboard!")

        # -- Actions --

        def _toggle_record(self) -> None:
            # Debounce: both pynput and Textual may fire for the same keypress
            now = time.monotonic()
            if now - self._last_toggle_time < 0.3:
                return
            self._last_toggle_time = now

            if self.engine.model is None:
                self._log_status("Model still loading, please wait...")
                return
            if self.state == "TRANSCRIBING":
                self._log_status("Still transcribing, please wait...")
                return

            if self.state == "IDLE":
                self.state = "RECORDING"
                self.engine.start_recording()
            else:
                self.state = "TRANSCRIBING"
                self.engine.stop_recording()
                self.run_worker(self._transcribe_worker, thread=True)

        async def _transcribe_worker(self) -> None:
            self.engine.transcribe()

        def action_toggle_record_binding(self) -> None:
            self._toggle_record()

        def action_quit_app(self) -> None:
            if self._listener:
                self._listener.stop()
            if self.engine.stream:
                self.engine.stream.stop()
                self.engine.stream.close()
            self.exit()

        def on_select_changed(self, event: Select.Changed) -> None:
            new_model = str(event.value)
            if new_model == self.engine.model_name:
                return
            if self.state != "IDLE":
                self._log_status("Cannot change model while recording/transcribing.")
                event.select.value = self.engine.model_name
                return
            self.engine.model_name = new_model
            self.engine.model = None
            self._log_status(f"Switching to model '{new_model}'...")
            self.run_worker(self._load_model_worker, thread=True)

    app = SpeechToTextApp(initial_model=model_name)
    app.run()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def run_headless(model_name="base", duration=None):
    """Record for a fixed duration (or until Enter), transcribe, print to stdout, and exit."""
    stt = SpeechToText(model_name=model_name)

    # Suppress status messages; only output the transcription
    stt.on_status = lambda msg: sys.stderr.write(f"{msg}\n")
    stt.on_transcription = lambda text, ts: print(text)

    stt.load_model()

    stt.start_recording()

    if duration:
        sys.stderr.write(f"Recording for {duration}s...\n")
        time.sleep(duration)
    else:
        sys.stderr.write("Recording... press Enter to stop.\n")
        input()

    stt.stop_recording()
    stt.transcribe()


def main():
    parser = argparse.ArgumentParser(description="sttui — Speech-to-Text TUI")
    parser.add_argument("--version", action="version", version=f"sttui {VERSION}")
    parser.add_argument("--cli", action="store_true", help="Run in CLI-only mode (no TUI)")
    parser.add_argument("--headless", action="store_true", help="Record, transcribe, print to stdout, and exit (no hotkeys/UI)")
    parser.add_argument("--duration", type=float, default=None, help="Recording duration in seconds (headless mode; omit to wait for Enter)")
    parser.add_argument("--model", default="base", choices=MODEL_SIZES, help="Whisper model size")
    args = parser.parse_args()

    if args.headless:
        run_headless(model_name=args.model, duration=args.duration)
    elif args.cli:
        run_cli(model_name=args.model)
    else:
        run_tui(model_name=args.model)


if __name__ == "__main__":
    main()
