#!/usr/bin/env python3
"""Fail if any reachable commit message contains a forbidden Cursor/AI Co-authored-by trailer."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent

# Co-authored-by: Cursor <cursoragent@cursor.com> and close variants
FORBIDDEN = re.compile(
    r"^Co-authored-by:\s*.*(?:cursoragent@cursor\.com|\bcursor\b)",
    re.IGNORECASE | re.MULTILINE,
)


def git_log_messages() -> list[tuple[str, str]]:
    proc = subprocess.run(
        ["git", "log", "--format=%H%x1f%B%x1e", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    entries = proc.stdout.strip("\x1e").split("\x1e")
    out: list[tuple[str, str]] = []
    for entry in entries:
        if not entry.strip():
            continue
        sha, _, body = entry.partition("\x1f")
        out.append((sha, body))
    return out


def hook_installed() -> bool:
    hook = REPO_ROOT / ".git" / "hooks" / "commit-msg"
    if not hook.is_file():
        return False
    try:
        text = hook.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return False
    return "cursoragent@cursor.com" in text or "Co-authored-by" in text


def main() -> int:
    bad: list[str] = []
    for sha, body in git_log_messages():
        if FORBIDDEN.search(body):
            bad.append(sha[:12])

    if not hook_installed():
        print("WARN commit-msg hook missing; run: builder/scripts/install_git_hooks.sh")

    if bad:
        print("FAIL forbidden Co-authored-by (Cursor/AI) in commits:", ", ".join(bad))
        print("Rewrite with: git filter-branch -f --msg-filter \\")
        print("  \"sed '/^Co-authored-by: Cursor <cursoragent@cursor.com>$/d'\" HEAD")
        return 1

    print("COMMIT COAUTHORS OK (no Cursor/AI trailers in history)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())