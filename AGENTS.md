# AGENTS.md

## Project

Neo Piano is a PyQt6/QML piano application for the NEO One education device
(ARM64/Armbian) and Linux desktops.

## Commands

```bash
make dev
make run
make test
make lint
make build
make deb
```

## Conventions

- Keep the QML UI independent from latency-sensitive input and audio processing.
- Do not perform blocking device or audio work on the Qt main thread.
- FluidSynth owns the real-time render thread; Python sends MIDI control events only.
- Keep audio tests independent of ALSA by injecting a fake synthesizer backend.
- Target Python 3.10 and Debian 12 (Bookworm) unless the deployment baseline changes.
- Use the `src/` layout, strict typing, and focused tests under `tests/unit/`.
- Never commit or push unless explicitly requested.
