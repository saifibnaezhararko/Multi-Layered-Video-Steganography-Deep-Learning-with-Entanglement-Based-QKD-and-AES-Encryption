import os
from pathlib import Path

'''
Output-path helpers shared by the audio and video steganography, so neither can
write over its own input files.
'''


def same_file(a, b):
    """True if both paths name one existing file (handles case-insensitive file systems and links)."""
    try:
        return os.path.samefile(a, b)
    except OSError:
        return False


def append_suffix(path, suffix):
    """Add suffix unless the path already has it: 'x.mp4' -> 'x.mp4.avi'.

    Appending (rather than replacing) never turns an output path into an input's path.
    """
    path = Path(path)
    return path if path.suffix.lower() == suffix else path.with_name(path.name + suffix)


def ensure_not_input(path, inputs):
    """Refuse to write path if it is one of the input files."""
    if any(p is not None and same_file(path, p) for p in inputs):
        raise ValueError(f"Output {path} would overwrite an input file; choose another output path")


def free_default(path, inputs):
    """path, or path_1, path_2, ... when a default output path is one of the inputs (e.g. re-hiding into a stego)."""
    path = Path(path)
    candidate, i = path, 1
    while any(p is not None and same_file(candidate, p) for p in inputs):
        candidate, i = path.with_name(f"{path.stem}_{i}{path.suffix}"), i + 1
    return candidate
