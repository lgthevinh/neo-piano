from pathlib import Path

import pytest

from neo_piano.audio import engine as engine_module
from neo_piano.audio.engine import AudioEngine
from neo_piano.audio.fluidsynth import FluidSynthError
from neo_piano.audio.outputs import AudioOutput
from neo_piano.audio.settings import AudioSettings
from neo_piano.audio.soundfonts import SoundFontNotFoundError


class FakeBackend:
    def __init__(self, fail_start: bool = False) -> None:
        self.fail_start = fail_start
        self.calls: list[tuple] = []

    def start(self) -> None:
        self.calls.append(("start",))
        if self.fail_start:
            raise RuntimeError("audio device busy")

    def note_on(self, note: int, velocity: int) -> None:
        self.calls.append(("note_on", note, velocity))

    def note_off(self, note: int) -> None:
        self.calls.append(("note_off", note))

    def sustain(self, enabled: bool) -> None:
        self.calls.append(("sustain", enabled))

    def all_notes_off(self) -> None:
        self.calls.append(("all_notes_off",))

    def set_gain(self, gain: float) -> None:
        self.calls.append(("set_gain", gain))

    def close(self) -> None:
        self.calls.append(("close",))


class ImmediateThread:
    def __init__(self, *, target, **_kwargs) -> None:
        self._target = target

    def start(self) -> None:
        self._target()


def test_audio_engine_controls_backend(monkeypatch, tmp_path: Path) -> None:
    soundfont = tmp_path / "piano.sf2"
    soundfont.write_bytes(b"sf2")
    backend = FakeBackend()
    monkeypatch.setattr(engine_module, "find_soundfont", lambda: soundfont)
    audio = AudioEngine(AudioSettings(), lambda _settings, _soundfont: backend)

    assert audio.start()
    assert audio.ready
    assert audio.statusMessage == "Audio ready"

    audio.noteOn(60, 100)
    audio.noteOn(60, 100)
    audio.setSustain(True)
    audio.noteOff(60)
    audio.noteOn(64, 90)
    audio.setVolume(72)
    audio.allNotesOff()
    audio.close()

    assert backend.calls == [
        ("start",),
        ("note_on", 60, 100),
        ("sustain", True),
        ("note_off", 60),
        ("note_on", 64, 90),
        ("set_gain", 0.72),
        ("all_notes_off",),
        ("close",),
    ]
    assert not audio.ready
    assert audio.statusMessage == "Audio stopped"
    assert audio.volume == 72


def test_audio_engine_degrades_when_backend_fails(monkeypatch, tmp_path: Path) -> None:
    soundfont = tmp_path / "piano.sf2"
    soundfont.write_bytes(b"sf2")
    backend = FakeBackend(fail_start=True)
    monkeypatch.setattr(engine_module, "find_soundfont", lambda: soundfont)
    audio = AudioEngine(AudioSettings(), lambda _settings, _soundfont: backend)

    assert not audio.start()
    assert not audio.ready
    assert audio.statusMessage == "Audio unavailable"


@pytest.mark.parametrize(
    ("error", "status"),
    [
        (SoundFontNotFoundError("no SoundFont found"), "SoundFont missing"),
        (FluidSynthError("libfluidsynth is not installed"), "FluidSynth missing"),
        (FluidSynthError("cannot start the alsa audio driver"), "Audio unavailable"),
    ],
)
def test_audio_engine_reports_actionable_error_status(error: Exception, status: str) -> None:
    assert AudioEngine._error_status(error) == status


@pytest.mark.parametrize(("note", "velocity"), [(-1, 100), (128, 100), (60, -1), (60, 128)])
def test_audio_engine_validates_midi_values(note: int, velocity: int) -> None:
    audio = AudioEngine(AudioSettings())

    with pytest.raises(ValueError):
        audio.noteOn(note, velocity)


@pytest.mark.parametrize("volume", [-1, 101])
def test_audio_engine_validates_volume(volume: int) -> None:
    audio = AudioEngine(AudioSettings())

    with pytest.raises(ValueError, match="volume must be between 0 and 100"):
        audio.setVolume(volume)


def test_audio_engine_exposes_discovered_outputs() -> None:
    audio = AudioEngine(AudioSettings())

    audio._apply_output_devices(
        [
            AudioOutput("alsa_output.h616", "NEO One speakers"),
            AudioOutput("alsa_output.hdmi", "HDMI"),
        ]
    )

    assert audio.outputDevices == [
        {"name": "default", "description": "System default"},
        {"name": "alsa_output.h616", "description": "NEO One speakers"},
        {"name": "alsa_output.hdmi", "description": "HDMI"},
    ]


def test_audio_engine_switches_output_without_blocking_qt_thread(
    monkeypatch, tmp_path: Path
) -> None:
    soundfont = tmp_path / "piano.sf2"
    soundfont.write_bytes(b"sf2")
    backends: list[FakeBackend] = []
    settings_seen: list[AudioSettings] = []

    def factory(settings: AudioSettings, _soundfont: Path) -> FakeBackend:
        settings_seen.append(settings)
        backend = FakeBackend()
        backends.append(backend)
        return backend

    monkeypatch.setattr(engine_module, "find_soundfont", lambda: soundfont)
    monkeypatch.setattr(engine_module, "Thread", ImmediateThread)
    audio = AudioEngine(AudioSettings(), factory)
    assert audio.start()

    audio.setOutputDevice("alsa_output.h616")

    assert audio.ready
    assert not audio.outputSwitching
    assert audio.selectedOutputDevice == "alsa_output.h616"
    assert [settings.device for settings in settings_seen] == ["default", "alsa_output.h616"]
    assert backends[0].calls == [("start",), ("all_notes_off",), ("close",)]
    assert backends[1].calls == [("start",)]


def test_audio_engine_loads_saved_output_device(monkeypatch) -> None:
    class FakePreferences:
        def value(self, key: str):
            assert key == "audio/outputDevice"
            return "alsa_output.h616"

        def setValue(self, _key: str, _value: str) -> None:  # noqa: N802
            pass

    monkeypatch.delenv("NEO_PIANO_AUDIO_DEVICE", raising=False)
    monkeypatch.setattr(engine_module, "QSettings", FakePreferences)

    audio = AudioEngine()

    assert audio.selectedOutputDevice == "alsa_output.h616"


def test_audio_engine_restores_previous_output_when_switch_fails(
    monkeypatch, tmp_path: Path
) -> None:
    soundfont = tmp_path / "piano.sf2"
    soundfont.write_bytes(b"sf2")
    created = 0

    def factory(_settings: AudioSettings, _soundfont: Path) -> FakeBackend:
        nonlocal created
        created += 1
        return FakeBackend(fail_start=created == 2)

    monkeypatch.setattr(engine_module, "find_soundfont", lambda: soundfont)
    monkeypatch.setattr(engine_module, "Thread", ImmediateThread)
    audio = AudioEngine(AudioSettings(), factory)
    assert audio.start()

    audio.setOutputDevice("alsa_output.unavailable")

    assert audio.ready
    assert audio.selectedOutputDevice == "default"
    assert created == 3
