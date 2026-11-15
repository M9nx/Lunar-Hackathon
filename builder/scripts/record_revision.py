#!/usr/bin/env python3
"""Record the exact tested revision: HEAD, dirty flag, and a digest of the working tree.

A clean tree is identified by HEAD alone. A dirty tree also gets a SHA-256 over the
tracked diff and every untracked file under the code paths (path and bytes), so evidence
names the exact code that was tested.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
# The digest covers code that is tested. Evidence and docs are outputs, not inputs.
CODE_PATHS = ("src/", "tests/", "web/", "builder/scripts/", "Master-Reference/")
SKIP = ("__pycache__/", ".pytest_cache/")


def _git(*args: str, binary: bool = False):
    out = subprocess.check_output(["git", *args], cwd=REPO)
    return out if binary else out.decode()


def revision_record() -> dict:
    head = _git("rev-parse", "HEAD").strip()
    short = _git("rev-parse", "--short", "HEAD").strip()
    branch = _git("rev-parse", "--abbrev-ref", "HEAD").strip()
    status = [line for line in _git("status", "--porcelain").splitlines() if line.strip()]
    dirty = bool(status)
    record = {
        "head": head,
        "head_short": short,
        "branch": branch,
        "dirty": dirty,
        "label": f"{short}-dirty" if dirty else short,
        "witnessed_replay_revision": "1f3fb06",
    }
    if dirty:
        digest = hashlib.sha256()
        digest.update(_git("diff", "HEAD", "--", *CODE_PATHS, binary=True))
        untracked = _git("ls-files", "--others", "--exclude-standard", "--", *CODE_PATHS).splitlines()
        for name in sorted(untracked):
            if any(part in name for part in SKIP):
                continue
            path = REPO / name
            if path.is_file():
                digest.update(name.encode() + b"\0" + path.read_bytes() + b"\0")
        record["code_digest_sha256"] = digest.hexdigest()
        record["code_paths"] = list(CODE_PATHS)
        record["changed_files"] = [line[3:] for line in status]
    return record


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", action="store_true", help="Print only the revision label")
    args = parser.parse_args()
    record = revision_record()
    print(record["label"] if args.label else json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
