# sttui
 ## Speech To Text Terminal User Interface
 ## prounounced like STEWIE

 **v0.1.0** | Python 3.10+ | MIT License

A local, fully offline speech-to-text tool powered by [faster-whisper](https://github.com/SYSTRAN/faster-whisper). Record audio with a global hotkey from any window, transcribe it on-device, and get the result copied straight to your clipboard — no cloud, no API keys, no latency.

Comes with a polished terminal UI built on [Textual](https://github.com/Textualize/textual), complete with a live audio level meter, transcription history, and on-the-fly model switching.

<!-- Replace with actual screenshot -->
<p align="center">
  <img src="screenshot.png" alt="sttui in action" width="700">
</p>

---

## Features

- **Fully offline** — runs entirely on your machine using faster-whisper with int8 quantization. No data ever leaves your device.
- **Global hotkeys** — record from anywhere without focusing the terminal
- **Live audio meter** — real-time visual feedback while recording
- **Transcription history** — timestamped, scrollable log of every dictation
- **Model switching** — swap between `tiny`, `base`, `small`, `medium`, and `large` whisper models on the fly
- **Clipboard integration** — transcriptions are automatically copied and ready to paste
- **Cross-platform** — works on Windows, macOS, and Linux
- **Three modes** — rich TUI (default), lightweight CLI (`--cli`), or headless (`--headless`) for scripting/piping

## Quick Start

```bash
git clone https://github.com/your-username/fasterwhisper-speech-to-text-tui.git
cd fasterwhisper-speech-to-text-tui
chmod +x install.sh run.sh
./install.sh
./run.sh
```

> On Windows, use Git Bash or MSYS2. On first run without a venv, `run.sh` will prompt to run `install.sh` for you.

## Usage

### Hotkeys

These work **globally** — even when the terminal is not focused:

| Hotkey | Action |
|---|---|
| `Ctrl+Shift+Space` | Start / stop recording |
| `Ctrl+C` | Quit |

### Workflow

1. Launch the tool — the whisper model loads in the background
2. Switch to any application (browser, editor, chat, etc.)
3. Press **Ctrl+Shift+Space** to start recording
4. Speak
5. Press **Ctrl+Shift+Space** again to stop
6. The transcription is copied to your clipboard — paste with **Ctrl+V**

### TUI Mode (default)

```bash
./run.sh
```

The terminal interface includes:
- **Model selector** — dropdown to switch whisper models without restarting
- **Status badge** — shows IDLE / RECORDING / TRANSCRIBING state
- **Level meter** — live audio input visualization
- **Transcription history** — scrollable log with timestamps
- **Status log** — model loading progress and system messages

### CLI Mode

```bash
./run.sh --cli
```

Minimal output, no UI — just hotkeys and clipboard.

### Headless Mode

Record, transcribe, print to stdout, and exit. No hotkeys or UI — ideal for scripts and piping.

```bash
# Record until Enter is pressed
./run.sh --headless

# Record for exactly 10 seconds
./run.sh --headless --duration 10

# Pipe transcription to another command
./run.sh --headless --duration 5 | xargs echo "You said:"
```

Status messages go to stderr, transcription goes to stdout.

### Options

| Flag | Description | Default |
|---|---|---|
| `--cli` | Run in CLI-only mode (no TUI) | off |
| `--headless` | Record, transcribe, print to stdout, and exit | off |
| `--duration` | Recording duration in seconds (headless mode; omit to wait for Enter) | — |
| `--model` | Whisper model size | `base` |
| `--version` | Print version and exit | — |

```bash
# Example: launch with the small model
./run.sh --model small
```

## Model Sizes

Larger models are more accurate but slower to load and transcribe. All models run on CPU with int8 quantization.

| Model | Parameters | Speed |
|---|---|---|
| `tiny` | 39M | Fastest |
| `base` | 74M | Fast |
| `small` | 244M | Moderate |
| `medium` | 769M | Slow |
| `large` | 1550M | Slowest |

In TUI mode you can switch models from the dropdown at any time.

## Scripts

| Script | Description |
|---|---|
| `install.sh` | Set up venv, install deps, and print `sttui` alias instructions |
| `run.sh` | Launch the app (prompts to install if no venv found) |
| `update.sh` | Pull latest changes and upgrade dependencies |
| `clean.sh` | Remove venv, cache, and logs (keeps source files) |
| `uninstall.sh` | Remove the entire project directory |

## Platform Notes

| Platform | Notes |
|---|---|
| **Windows** | Works out of the box via Git Bash or MSYS2. |
| **macOS** | Clipboard works via `pbcopy`. You may need to grant terminal accessibility permissions for global hotkeys. |
| **Linux** | Install `xclip` or `xsel` for clipboard support (`sudo apt install xclip`). |

## Transcription Log

All transcriptions are automatically saved to `transcription_log.txt` with timestamps for reference.

## License

MIT
