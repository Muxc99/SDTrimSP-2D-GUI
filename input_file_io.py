"""Deterministic text writes for Fortran input files on Windows and WSL."""
from pathlib import Path
import os
import uuid


def normalized_input_text(text):
    """Return UTF-8 text with one LF per logical line and no stray CR bytes."""
    if not isinstance(text, str):
        raise TypeError('Input content must be text.')
    return text.replace('\r\n', '\n').replace('\r', '\n')


def atomic_write_text(path, text, encoding='utf-8'):
    """Write normalized text atomically, without platform newline conversion."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    data = normalized_input_text(text).encode(encoding)
    temporary = target.parent / ('.' + target.name + '.gui-write-' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)
