from pathlib import Path

import pytest

from neo_piano.audio.fluidsynth import FluidSynthBackend, FluidSynthError
from neo_piano.audio.settings import AudioSettings


class FakeFunction:
    def __init__(self, result=None) -> None:
        self.result = result
        self.calls: list[tuple] = []
        self.argtypes = None
        self.restype = None

    def __call__(self, *arguments):
        self.calls.append(arguments)
        return self.result


class FakeLibrary:
    def __init__(self, soundfont_result: int = 3) -> None:
        self.new_fluid_settings = FakeFunction(1)
        self.delete_fluid_settings = FakeFunction()
        self.fluid_settings_setstr = FakeFunction(0)
        self.fluid_settings_setint = FakeFunction(0)
        self.fluid_settings_setnum = FakeFunction(0)
        self.new_fluid_synth = FakeFunction(2)
        self.delete_fluid_synth = FakeFunction()
        self.fluid_synth_sfload = FakeFunction(soundfont_result)
        self.fluid_synth_program_select = FakeFunction(0)
        self.new_fluid_audio_driver = FakeFunction(4)
        self.delete_fluid_audio_driver = FakeFunction()
        self.fluid_synth_noteon = FakeFunction(0)
        self.fluid_synth_noteoff = FakeFunction(0)
        self.fluid_synth_cc = FakeFunction(0)
        self.fluid_synth_set_gain = FakeFunction()


def test_fluidsynth_backend_lifecycle(tmp_path: Path) -> None:
    library = FakeLibrary()
    soundfont = tmp_path / "piano.sf2"
    backend = FluidSynthBackend(AudioSettings(), soundfont, library)

    backend.start()
    backend.note_on(60, 100)
    backend.note_off(60)
    backend.sustain(True)
    backend.set_gain(0.72)
    backend.all_notes_off()
    backend.close()

    assert library.fluid_synth_sfload.calls == [(2, str(soundfont).encode(), 1)]
    assert (1, b"audio.pulseaudio.device", b"default") in library.fluid_settings_setstr.calls
    assert library.fluid_synth_program_select.calls == [(2, 0, 3, 0, 0)]
    assert library.fluid_synth_noteon.calls == [(2, 0, 60, 100)]
    assert library.fluid_synth_noteoff.calls == [(2, 0, 60)]
    assert library.fluid_synth_set_gain.calls == [(2, 0.72)]
    assert library.fluid_synth_cc.calls == [(2, 0, 64, 127), (2, 0, 64, 0), (2, 0, 123, 0)]
    assert library.delete_fluid_audio_driver.calls == [(4,)]
    assert library.delete_fluid_synth.calls == [(2,)]
    assert library.delete_fluid_settings.calls == [(1,)]


def test_fluidsynth_backend_cleans_up_failed_start(tmp_path: Path) -> None:
    library = FakeLibrary(soundfont_result=-1)
    backend = FluidSynthBackend(AudioSettings(), tmp_path / "missing.sf2", library)

    with pytest.raises(FluidSynthError, match="cannot load SoundFont"):
        backend.start()

    assert library.delete_fluid_synth.calls == [(2,)]
    assert library.delete_fluid_settings.calls == [(1,)]


def test_fluidsynth_note_off_allows_an_already_ended_voice(tmp_path: Path) -> None:
    library = FakeLibrary()
    library.fluid_synth_noteoff.result = -1
    backend = FluidSynthBackend(AudioSettings(), tmp_path / "piano.sf2", library)
    backend.start()

    backend.note_off(60)

    assert library.fluid_synth_noteoff.calls == [(2, 0, 60)]


def test_fluidsynth_selects_alsa_device(tmp_path: Path) -> None:
    library = FakeLibrary()
    settings = AudioSettings(driver="alsa", device="plughw:1")
    backend = FluidSynthBackend(settings, tmp_path / "piano.sf2", library)

    backend.start()

    assert (1, b"audio.alsa.device", b"plughw:1") in library.fluid_settings_setstr.calls
