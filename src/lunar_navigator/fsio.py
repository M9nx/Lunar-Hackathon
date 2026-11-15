"""Atomic file publication. A failed or interrupted write leaves the previous file intact."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path


def _fsync_dir(directory: Path) -> None:
    try:
        fd = os.open(directory, os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(fd)
    except OSError:
        pass
    finally:
        os.close(fd)


def stage_text(path: Path, text: str) -> Path:
    """Write text to a temp file beside path. The destination is not touched."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp = Path(tmp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(tmp, 0o644)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    return tmp


def atomic_write_text(path: Path, text: str) -> None:
    tmp = stage_text(path, text)
    try:
        os.replace(tmp, path)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    _fsync_dir(path.parent)


def atomic_write_json(path: Path, payload: dict) -> None:
    # Serialize first: a payload that cannot be encoded never reaches disk.
    atomic_write_text(path, json.dumps(payload, indent=2) + "\n")


def atomic_write_json_set(items: list[tuple[Path, dict]]) -> None:
    """Stage every file, then publish with renames in the given order.

    Nothing visible changes until all files are staged. Put the entry file
    (for example comparison.json) last. Only renames remain in the publish
    phase, so a failure while staging keeps the previous set whole.
    """
    texts = [(path, json.dumps(payload, indent=2) + "\n") for path, payload in items]
    staged: list[tuple[Path, Path]] = []
    try:
        for path, text in texts:
            staged.append((path, stage_text(path, text)))
        for path, tmp in staged:
            os.replace(tmp, path)
        staged = []
    finally:
        for _, tmp in staged:
            tmp.unlink(missing_ok=True)
    for directory in {path.parent for path, _ in items}:
        _fsync_dir(directory)
