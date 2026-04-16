# Changelog

All notable changes to stttui are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.3.0] - 2026-04-16

### Added
- Single-instance enforcement. A second invocation of `stttui` now fails fast
  with `stttui is already running (PID N). Stop the other instance or
  kill N first.` instead of silently fighting the existing instance for the
  global hotkey and audio device. Works across the TUI, CLI, and headless
  modes. Implemented via an atomic PID lockfile at `~/.stttui/stttui.lock`
  with stale-PID recovery. No new dependencies.

### Fixed
- `stttui --cli` now cleans up properly on `Ctrl+C`. The SIGINT handler was
  calling `os._exit(0)`, which skipped `atexit` and would have stranded the
  new singleton lockfile on every quit.

## [0.2.0] - 2026-03-21

- Initial public release.
