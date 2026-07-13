import ctypes
import ctypes.util
from pathlib import Path
from typing import Any

from neo_piano.audio.settings import AudioSettings


class FluidSynthError(RuntimeError):
    """Raised when the native FluidSynth backend cannot complete an operation."""


def _load_library() -> Any:
    library_name = ctypes.util.find_library("fluidsynth")
    if not library_name:
        raise FluidSynthError("libfluidsynth is not installed")
    try:
        return ctypes.CDLL(library_name)
    except OSError as error:
        raise FluidSynthError(f"cannot load {library_name}: {error}") from error


class FluidSynthBackend:
    """Small direct binding to the stable libfluidsynth C API."""

    def __init__(
        self,
        settings: AudioSettings,
        soundfont: Path,
        library: Any | None = None,
    ) -> None:
        self._config = settings
        self._soundfont = soundfont
        self._library = library if library is not None else _load_library()
        self._settings: int | None = None
        self._synth: int | None = None
        self._driver: int | None = None
        self._configure_api()

    def _configure_api(self) -> None:
        pointer = ctypes.c_void_p
        functions = {
            "new_fluid_settings": ([], pointer),
            "delete_fluid_settings": ([pointer], None),
            "fluid_settings_setstr": ([pointer, ctypes.c_char_p, ctypes.c_char_p], ctypes.c_int),
            "fluid_settings_setint": ([pointer, ctypes.c_char_p, ctypes.c_int], ctypes.c_int),
            "fluid_settings_setnum": ([pointer, ctypes.c_char_p, ctypes.c_double], ctypes.c_int),
            "new_fluid_synth": ([pointer], pointer),
            "delete_fluid_synth": ([pointer], None),
            "fluid_synth_sfload": ([pointer, ctypes.c_char_p, ctypes.c_int], ctypes.c_int),
            "fluid_synth_program_select": (
                [pointer, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int],
                ctypes.c_int,
            ),
            "new_fluid_audio_driver": ([pointer, pointer], pointer),
            "delete_fluid_audio_driver": ([pointer], None),
            "fluid_synth_noteon": (
                [pointer, ctypes.c_int, ctypes.c_int, ctypes.c_int],
                ctypes.c_int,
            ),
            "fluid_synth_noteoff": ([pointer, ctypes.c_int, ctypes.c_int], ctypes.c_int),
            "fluid_synth_cc": (
                [pointer, ctypes.c_int, ctypes.c_int, ctypes.c_int],
                ctypes.c_int,
            ),
            "fluid_synth_set_gain": ([pointer, ctypes.c_double], None),
        }
        for name, (argument_types, return_type) in functions.items():
            function = getattr(self._library, name)
            function.argtypes = argument_types
            function.restype = return_type

    def _set_string(self, name: str, value: str) -> None:
        if self._library.fluid_settings_setstr(
            self._settings, name.encode(), value.encode()
        ) < 0:
            raise FluidSynthError(f"unsupported FluidSynth setting: {name}={value}")

    def _set_integer(self, name: str, value: int) -> None:
        if self._library.fluid_settings_setint(self._settings, name.encode(), value) < 0:
            raise FluidSynthError(f"unsupported FluidSynth setting: {name}={value}")

    def _set_number(self, name: str, value: float) -> None:
        if self._library.fluid_settings_setnum(self._settings, name.encode(), value) < 0:
            raise FluidSynthError(f"unsupported FluidSynth setting: {name}={value}")

    def start(self) -> None:
        if self._driver is not None:
            return

        self._settings = self._library.new_fluid_settings()
        if self._settings is None:
            raise FluidSynthError("cannot create FluidSynth settings")

        try:
            self._set_string("audio.driver", self._config.driver)
            self._set_number("synth.sample-rate", float(self._config.sample_rate))
            self._set_integer("audio.period-size", self._config.period_size)
            self._set_integer("audio.periods", self._config.periods)
            self._set_integer("synth.polyphony", self._config.polyphony)
            self._set_integer("synth.cpu-cores", self._config.cpu_cores)
            self._set_integer("synth.threadsafe-api", 1)
            self._set_integer("synth.reverb.active", 0)
            self._set_integer("synth.chorus.active", 0)
            self._set_number("synth.gain", self._config.gain)

            self._synth = self._library.new_fluid_synth(self._settings)
            if self._synth is None:
                raise FluidSynthError("cannot create FluidSynth synthesizer")

            soundfont_id = self._library.fluid_synth_sfload(
                self._synth, str(self._soundfont).encode(), 1
            )
            if soundfont_id < 0:
                raise FluidSynthError(f"cannot load SoundFont: {self._soundfont}")

            if self._library.fluid_synth_program_select(
                self._synth, 0, soundfont_id, 0, 0
            ) < 0:
                raise FluidSynthError("cannot select the acoustic piano preset")

            self._driver = self._library.new_fluid_audio_driver(self._settings, self._synth)
            if self._driver is None:
                raise FluidSynthError(f"cannot start the {self._config.driver} audio driver")
        except Exception:
            self.close()
            raise

    def _require_synth(self) -> int:
        if self._synth is None:
            raise FluidSynthError("FluidSynth is not running")
        return self._synth

    def note_on(self, note: int, velocity: int) -> None:
        if self._library.fluid_synth_noteon(self._require_synth(), 0, note, velocity) < 0:
            raise FluidSynthError(f"note-on failed for MIDI note {note}")

    def note_off(self, note: int) -> None:
        # FLUID_FAILED also means the voice already ended, which is harmless.
        self._library.fluid_synth_noteoff(self._require_synth(), 0, note)

    def sustain(self, enabled: bool) -> None:
        value = 127 if enabled else 0
        if self._library.fluid_synth_cc(self._require_synth(), 0, 64, value) < 0:
            raise FluidSynthError("sustain control failed")

    def all_notes_off(self) -> None:
        synth = self._require_synth()
        self._library.fluid_synth_cc(synth, 0, 64, 0)
        if self._library.fluid_synth_cc(synth, 0, 123, 0) < 0:
            raise FluidSynthError("all-notes-off control failed")

    def set_gain(self, gain: float) -> None:
        self._library.fluid_synth_set_gain(self._require_synth(), gain)

    def close(self) -> None:
        if self._driver is not None:
            self._library.delete_fluid_audio_driver(self._driver)
            self._driver = None
        if self._synth is not None:
            self._library.delete_fluid_synth(self._synth)
            self._synth = None
        if self._settings is not None:
            self._library.delete_fluid_settings(self._settings)
            self._settings = None
