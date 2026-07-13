import logging
from dataclasses import replace
from pathlib import Path
from threading import RLock
from typing import Protocol

from PyQt6.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot  # type: ignore[attr-defined]

from neo_piano.audio.fluidsynth import FluidSynthBackend, FluidSynthError
from neo_piano.audio.settings import AudioSettings
from neo_piano.audio.soundfonts import SoundFontNotFoundError, find_soundfont

logger = logging.getLogger(__name__)


class SynthBackend(Protocol):
    def start(self) -> None: ...

    def note_on(self, note: int, velocity: int) -> None: ...

    def note_off(self, note: int) -> None: ...

    def sustain(self, enabled: bool) -> None: ...

    def all_notes_off(self) -> None: ...

    def set_gain(self, gain: float) -> None: ...

    def close(self) -> None: ...


class BackendFactory(Protocol):
    def __call__(self, settings: AudioSettings, soundfont: Path) -> SynthBackend: ...


class AudioEngine(QObject):
    """Qt-facing owner of the native real-time synthesizer."""

    readyChanged = pyqtSignal()  # noqa: N815
    statusMessageChanged = pyqtSignal()  # noqa: N815
    noteStateChanged = pyqtSignal(int, bool)  # noqa: N815
    volumeChanged = pyqtSignal()  # noqa: N815

    def __init__(
        self,
        settings: AudioSettings | None = None,
        backend_factory: BackendFactory = FluidSynthBackend,
    ) -> None:
        super().__init__()
        self._settings = settings or AudioSettings.from_environment()
        self._backend_factory = backend_factory
        self._backend: SynthBackend | None = None
        self._ready = False
        self._status_message = "Starting audio"
        self._volume = max(0, min(100, round(self._settings.gain * 100)))
        self._active_notes: set[int] = set()
        self._lock = RLock()

    @pyqtProperty(bool, notify=readyChanged)  # type: ignore[untyped-decorator]
    def ready(self) -> bool:
        return self._ready

    @pyqtProperty(str, notify=statusMessageChanged)  # type: ignore[untyped-decorator]
    def statusMessage(self) -> str:  # noqa: N802
        return self._status_message

    @pyqtProperty(int, notify=volumeChanged)  # type: ignore[untyped-decorator]
    def volume(self) -> int:
        return self._volume

    def _set_state(self, ready: bool, message: str) -> None:
        if self._ready != ready:
            self._ready = ready
            self.readyChanged.emit()
        if self._status_message != message:
            self._status_message = message
            self.statusMessageChanged.emit()

    @staticmethod
    def _error_status(error: Exception) -> str:
        if isinstance(error, SoundFontNotFoundError):
            return "SoundFont missing"
        if isinstance(error, FluidSynthError) and (
            "not installed" in str(error) or "cannot load" in str(error)
        ):
            return "FluidSynth missing"
        return "Audio unavailable"

    def start(self) -> bool:
        with self._lock:
            if self._ready:
                return True
            try:
                soundfont = find_soundfont()
                backend = self._backend_factory(self._settings, soundfont)
                backend.start()
            except (OSError, RuntimeError, ValueError) as error:
                logger.error("Audio unavailable: %s", error)
                self._backend = None
                self._set_state(False, self._error_status(error))
                return False

            self._backend = backend
            self._set_state(True, "Audio ready")
            logger.info("Audio ready with SoundFont %s", soundfont)
            return True

    @staticmethod
    def _validate_midi_value(name: str, value: int) -> None:
        if not 0 <= value <= 127:
            raise ValueError(f"{name} must be between 0 and 127")

    @pyqtSlot(int, int)
    def noteOn(self, note: int, velocity: int) -> None:  # noqa: N802
        self._validate_midi_value("note", note)
        self._validate_midi_value("velocity", velocity)
        with self._lock:
            if self._backend is None or note in self._active_notes:
                return
            self._backend.note_on(note, velocity)
            self._active_notes.add(note)
            self.noteStateChanged.emit(note, True)

    @pyqtSlot(int)
    def noteOff(self, note: int) -> None:  # noqa: N802
        self._validate_midi_value("note", note)
        with self._lock:
            if self._backend is None or note not in self._active_notes:
                return
            self._backend.note_off(note)
            self._active_notes.remove(note)
            self.noteStateChanged.emit(note, False)

    @pyqtSlot(bool)
    def setSustain(self, enabled: bool) -> None:  # noqa: N802
        with self._lock:
            if self._backend is not None:
                self._backend.sustain(enabled)

    @pyqtSlot(int)
    def setVolume(self, volume: int) -> None:  # noqa: N802
        if not 0 <= volume <= 100:
            raise ValueError("volume must be between 0 and 100")
        with self._lock:
            if self._volume == volume:
                return
            self._volume = volume
            self._settings = replace(self._settings, gain=volume / 100.0)
            if self._backend is not None:
                self._backend.set_gain(volume / 100.0)
            self.volumeChanged.emit()

    @pyqtSlot()
    def allNotesOff(self) -> None:  # noqa: N802
        with self._lock:
            if self._backend is not None:
                self._backend.all_notes_off()
            for note in self._active_notes:
                self.noteStateChanged.emit(note, False)
            self._active_notes.clear()

    @pyqtSlot()
    def close(self) -> None:
        with self._lock:
            if self._backend is not None:
                self._backend.close()
                self._backend = None
            self._active_notes.clear()
            self._set_state(False, "Audio stopped")
