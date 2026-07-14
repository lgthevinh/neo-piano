from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class AudioOutput:
    name: str
    description: str


class OutputProvider(Protocol):
    def list_outputs(self) -> list[AudioOutput]: ...


class PulseAudioOutputProvider:
    """Discover playback sinks through PulseAudio without depending on alsa-utils."""

    def list_outputs(self) -> list[AudioOutput]:
        import pulsectl

        try:
            with pulsectl.Pulse("neo-piano-device-list") as pulse:
                return [
                    AudioOutput(sink.name, sink.description or sink.name)
                    for sink in pulse.sink_list()
                ]
        except pulsectl.PulseError as error:
            raise RuntimeError(f"cannot query PulseAudio outputs: {error}") from error
