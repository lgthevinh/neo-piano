import os
import sys
from dataclasses import dataclass


def _default_driver() -> str:
    if sys.platform.startswith("linux"):
        return "pulseaudio"
    if sys.platform == "darwin":
        return "coreaudio"
    return "pulseaudio"


def _env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error


def _env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError as error:
        raise ValueError(f"{name} must be a number") from error


@dataclass(frozen=True, slots=True)
class AudioSettings:
    driver: str = "pulseaudio"
    device: str = "default"
    sample_rate: int = 48_000
    period_size: int = 128
    periods: int = 3
    polyphony: int = 64
    cpu_cores: int = 2
    gain: float = 1.0

    def __post_init__(self) -> None:
        if not self.driver:
            raise ValueError("audio driver cannot be empty")
        if not self.device:
            raise ValueError("audio device cannot be empty")
        if self.sample_rate <= 0:
            raise ValueError("sample rate must be positive")
        if self.period_size < 64:
            raise ValueError("period size must be at least 64 samples")
        if self.periods < 2:
            raise ValueError("at least two audio periods are required")
        if self.polyphony <= 0:
            raise ValueError("polyphony must be positive")
        if self.cpu_cores <= 0:
            raise ValueError("CPU core count must be positive")
        if not 0.0 <= self.gain <= 10.0:
            raise ValueError("gain must be between 0 and 10")

    @classmethod
    def from_environment(cls) -> "AudioSettings":
        return cls(
            driver=os.environ.get("NEO_PIANO_AUDIO_DRIVER", _default_driver()),
            device=os.environ.get("NEO_PIANO_AUDIO_DEVICE", "default"),
            sample_rate=_env_int("NEO_PIANO_SAMPLE_RATE", 48_000),
            period_size=_env_int("NEO_PIANO_PERIOD_SIZE", 128),
            periods=_env_int("NEO_PIANO_PERIODS", 3),
            polyphony=_env_int("NEO_PIANO_POLYPHONY", 64),
            cpu_cores=_env_int("NEO_PIANO_CPU_CORES", 2),
            gain=_env_float("NEO_PIANO_GAIN", 1.0),
        )
