from pathlib import Path

import pytest

from neo_piano.audio.soundfonts import SoundFontNotFoundError, find_soundfont


def test_configured_soundfont_takes_precedence(monkeypatch, tmp_path: Path) -> None:
    configured = tmp_path / "piano.sf2"
    configured.write_bytes(b"sf2")
    fallback = tmp_path / "fallback.sf2"
    fallback.write_bytes(b"sf2")
    monkeypatch.setenv("NEO_PIANO_SOUNDFONT", str(configured))

    assert find_soundfont([fallback]) == configured


def test_find_soundfont_uses_first_existing_candidate(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.delenv("NEO_PIANO_SOUNDFONT", raising=False)
    existing = tmp_path / "piano.sf2"
    existing.write_bytes(b"sf2")

    assert find_soundfont([tmp_path / "missing.sf2", existing]) == existing


def test_find_soundfont_reports_missing_configured_file(monkeypatch, tmp_path: Path) -> None:
    missing = tmp_path / "missing.sf2"
    monkeypatch.setenv("NEO_PIANO_SOUNDFONT", str(missing))

    with pytest.raises(SoundFontNotFoundError, match="configured SoundFont"):
        find_soundfont([])


def test_find_soundfont_reports_no_candidates(monkeypatch) -> None:
    monkeypatch.delenv("NEO_PIANO_SOUNDFONT", raising=False)

    with pytest.raises(SoundFontNotFoundError, match="no SoundFont found"):
        find_soundfont([])

