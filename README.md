# NEO Piano

NEO Piano is a piano application for the ARM64/Armbian-based NEO One education
device. It uses Python, PyQt6, and Qt Quick/QML.

Audio is rendered by FluidSynth through PulseAudio on Linux so it can coexist
with desktop audio and switch between the NEO One's onboard and HDMI outputs.
The Debian package installs the native library and the compact TimGM6mb
SoundFont automatically.

## Development

Python 3.10 or newer is required.

On Fedora, install the native audio runtime once:

```bash
sudo dnf install fluidsynth fluid-soundfont-gm
```

The Debian package installs the equivalent runtime dependencies automatically.

```bash
python3 -m venv .venv
source .venv/bin/activate
make dev
make run
```

## Verification

```bash
make test
make lint
make build
```

## Debian 12 package

Docker or Podman is required:

```bash
make deb
```

The resulting `.deb` is written to `dist/` and can be installed with `apt` on
the NEO One.

## Audio tuning

The default audio buffer is 3 periods of 128 samples at 48 kHz. The following
environment variables can be used for measurements on the target device:

```text
NEO_PIANO_SOUNDFONT
NEO_PIANO_AUDIO_DRIVER
NEO_PIANO_AUDIO_DEVICE
NEO_PIANO_SAMPLE_RATE
NEO_PIANO_PERIOD_SIZE
NEO_PIANO_PERIODS
NEO_PIANO_POLYPHONY
NEO_PIANO_CPU_CORES
NEO_PIANO_GAIN
```

The default five-key layout maps the arrow keys and Space to white piano keys.
The control panel can expand the board to 8 or 12 white keys. Press Escape to
stop all notes. On PulseAudio systems, the control panel also lists available
audio outputs and remembers the selected output for the next launch.

## Install on NEO One

```bash
curl -fsSL https://raw.githubusercontent.com/lgthevinh/neo-piano/main/scripts/install_on_neo.sh | bash
```

Install a specific version with `--version=X.Y.Z`, or remove the app with
`--uninstall`.
