import os
from collections.abc import Iterable
from pathlib import Path

SOUNDFONT_ENVIRONMENT_VARIABLE = "NEO_PIANO_SOUNDFONT"

SYSTEM_SOUNDFONTS = (
    Path("/usr/share/sounds/sf2/TimGM6mb.sf2"),
    Path("/usr/share/sounds/sf2/FluidR3_GM.sf2"),
    Path("/usr/share/soundfonts/FluidR3_GM.sf2"),
    Path("/usr/share/soundfonts/default.sf2"),
    Path("/usr/share/sounds/sf2/default.sf2"),
)


class SoundFontNotFoundError(FileNotFoundError):
    """Raised when no usable SoundFont can be found."""


def find_soundfont(candidates: Iterable[Path] = SYSTEM_SOUNDFONTS) -> Path:
    """Find the configured SoundFont or a supported system SoundFont."""
    configured = os.environ.get(SOUNDFONT_ENVIRONMENT_VARIABLE)
    if configured:
        path = Path(configured).expanduser()
        if path.is_file():
            return path
        raise SoundFontNotFoundError(f"configured SoundFont does not exist: {path}")

    for path in candidates:
        if path.is_file():
            return path

    raise SoundFontNotFoundError(
        f"no SoundFont found; set {SOUNDFONT_ENVIRONMENT_VARIABLE} to an SF2 file"
    )
