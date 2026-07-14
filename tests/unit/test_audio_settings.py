import pytest

from neo_piano.audio.settings import AudioSettings


def test_audio_settings_load_environment(monkeypatch) -> None:
    monkeypatch.setenv("NEO_PIANO_AUDIO_DRIVER", "pulseaudio")
    monkeypatch.setenv("NEO_PIANO_AUDIO_DEVICE", "alsa_output.h616")
    monkeypatch.setenv("NEO_PIANO_SAMPLE_RATE", "44100")
    monkeypatch.setenv("NEO_PIANO_PERIOD_SIZE", "64")
    monkeypatch.setenv("NEO_PIANO_PERIODS", "4")
    monkeypatch.setenv("NEO_PIANO_POLYPHONY", "32")
    monkeypatch.setenv("NEO_PIANO_CPU_CORES", "1")
    monkeypatch.setenv("NEO_PIANO_GAIN", "0.7")

    settings = AudioSettings.from_environment()

    assert settings.driver == "pulseaudio"
    assert settings.device == "alsa_output.h616"
    assert settings.sample_rate == 44_100
    assert settings.period_size == 64
    assert settings.periods == 4
    assert settings.polyphony == 32
    assert settings.cpu_cores == 1
    assert settings.gain == 0.7


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("period_size", 32),
        ("periods", 1),
        ("polyphony", 0),
        ("cpu_cores", 0),
        ("gain", 11.0),
    ],
)
def test_audio_settings_reject_invalid_values(field, value) -> None:
    values = {field: value}
    with pytest.raises(ValueError):
        AudioSettings(**values)


def test_audio_settings_reject_non_numeric_environment(monkeypatch) -> None:
    monkeypatch.setenv("NEO_PIANO_PERIOD_SIZE", "fast")

    with pytest.raises(ValueError, match="NEO_PIANO_PERIOD_SIZE must be an integer"):
        AudioSettings.from_environment()
