import logging
import os
from dataclasses import replace
from pathlib import Path
from threading import RLock, Thread
from typing import Protocol

from PyQt6.QtCore import (  # type: ignore[attr-defined]
    QObject,
    QSettings,
    pyqtProperty,
    pyqtSignal,
    pyqtSlot,
)

from neo_piano.audio.fluidsynth import FluidSynthBackend, FluidSynthError
from neo_piano.audio.outputs import AudioOutput, OutputProvider, PulseAudioOutputProvider
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
    outputDevicesChanged = pyqtSignal()  # noqa: N815
    selectedOutputDeviceChanged = pyqtSignal()  # noqa: N815
    outputSwitchingChanged = pyqtSignal()  # noqa: N815
    _outputsLoaded = pyqtSignal(object)  # noqa: N815
    _outputSwitchFinished = pyqtSignal(str, bool, str, bool)  # noqa: N815

    def __init__(
        self,
        settings: AudioSettings | None = None,
        backend_factory: BackendFactory = FluidSynthBackend,
        output_provider: OutputProvider | None = None,
    ) -> None:
        super().__init__()
        self._settings = settings or AudioSettings.from_environment()
        self._preferences = QSettings()
        self._persist_output_device = settings is None and "NEO_PIANO_AUDIO_DEVICE" not in os.environ
        if self._persist_output_device:
            saved_device = self._preferences.value("audio/outputDevice")
            if isinstance(saved_device, str) and saved_device:
                self._settings = replace(self._settings, device=saved_device)
        self._backend_factory = backend_factory
        self._output_provider = output_provider or PulseAudioOutputProvider()
        self._backend: SynthBackend | None = None
        self._ready = False
        self._status_message = "Starting audio"
        self._volume = max(0, min(100, round(self._settings.gain * 100)))
        self._active_notes: set[int] = set()
        self._lock = RLock()
        self._output_devices = [AudioOutput("default", "System default")]
        self._output_switching = False
        self._closing = False
        self._outputsLoaded.connect(self._apply_output_devices)
        self._outputSwitchFinished.connect(self._finish_output_switch)

    @pyqtProperty(bool, notify=readyChanged)  # type: ignore[untyped-decorator]
    def ready(self) -> bool:
        return self._ready

    @pyqtProperty(str, notify=statusMessageChanged)  # type: ignore[untyped-decorator]
    def statusMessage(self) -> str:  # noqa: N802
        return self._status_message

    @pyqtProperty(int, notify=volumeChanged)  # type: ignore[untyped-decorator]
    def volume(self) -> int:
        return self._volume

    @pyqtProperty("QVariantList", notify=outputDevicesChanged)  # type: ignore[untyped-decorator]
    def outputDevices(self) -> list[dict[str, str]]:  # noqa: N802
        return [
            {"name": output.name, "description": output.description}
            for output in self._output_devices
        ]

    @pyqtProperty(str, notify=selectedOutputDeviceChanged)  # type: ignore[untyped-decorator]
    def selectedOutputDevice(self) -> str:  # noqa: N802
        return self._settings.device

    @pyqtProperty(bool, notify=outputSwitchingChanged)  # type: ignore[untyped-decorator]
    def outputSwitching(self) -> bool:  # noqa: N802
        return self._output_switching

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
    def refreshOutputDevices(self) -> None:  # noqa: N802
        if self._settings.driver != "pulseaudio":
            return

        def load() -> None:
            try:
                outputs = self._output_provider.list_outputs()
            except (OSError, RuntimeError) as error:
                logger.warning("Cannot list PulseAudio outputs: %s", error)
                outputs = []
            self._outputsLoaded.emit(outputs)

        Thread(target=load, name="neo-piano-output-list", daemon=True).start()

    @pyqtSlot(object)
    def _apply_output_devices(self, outputs: object) -> None:
        discovered = outputs if isinstance(outputs, list) else []
        devices = [AudioOutput("default", "System default")]
        devices.extend(output for output in discovered if isinstance(output, AudioOutput))
        if devices != self._output_devices:
            self._output_devices = devices
            self.outputDevicesChanged.emit()

    @pyqtSlot(str)
    def setOutputDevice(self, device: str) -> None:  # noqa: N802
        if not device or device == self._settings.device or self._output_switching:
            return
        self.allNotesOff()
        self._output_switching = True
        self.outputSwitchingChanged.emit()
        self._set_state(False, "Switching audio output")

        def switch() -> None:
            error_message = ""
            success = False
            fallback_ready = False
            next_settings = replace(self._settings, device=device)
            with self._lock:
                try:
                    if self._backend is not None:
                        self._backend.close()
                    self._backend = None
                    soundfont = find_soundfont()
                    backend = self._backend_factory(next_settings, soundfont)
                    backend.start()
                    self._backend = backend
                    success = True
                except (OSError, RuntimeError, ValueError) as error:
                    logger.error("Cannot switch audio output to %s: %s", device, error)
                    error_message = self._error_status(error)
                    try:
                        soundfont = find_soundfont()
                        fallback = self._backend_factory(self._settings, soundfont)
                        fallback.start()
                        self._backend = fallback
                        fallback_ready = True
                    except (OSError, RuntimeError, ValueError) as fallback_error:
                        logger.error("Cannot restore previous audio output: %s", fallback_error)
            self._outputSwitchFinished.emit(device, success, error_message, fallback_ready)

        Thread(target=switch, name="neo-piano-output-switch", daemon=True).start()

    @pyqtSlot(str, bool, str, bool)
    def _finish_output_switch(
        self, device: str, success: bool, error_message: str, fallback_ready: bool
    ) -> None:
        self._output_switching = False
        self.outputSwitchingChanged.emit()
        if self._closing:
            return
        if success:
            self._settings = replace(self._settings, device=device)
            if self._persist_output_device:
                self._preferences.setValue("audio/outputDevice", device)
            self.selectedOutputDeviceChanged.emit()
            self._set_state(True, "Audio ready")
        elif fallback_ready:
            self.selectedOutputDeviceChanged.emit()
            self._set_state(True, "Audio ready")
        else:
            self._set_state(False, error_message or "Audio unavailable")

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
        self._closing = True
        with self._lock:
            if self._backend is not None:
                self._backend.close()
                self._backend = None
            self._active_notes.clear()
            self._set_state(False, "Audio stopped")
