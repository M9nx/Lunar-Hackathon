#!/usr/bin/env bash
# Install tracked git hooks into .git/hooks (does not change global or local git config).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
SRC="$ROOT/builder/git-hooks"
DST="$ROOT/.git/hooks"
mkdir -p "$DST"
for hook in prepare-commit-msg commit-msg; do
  cp "$SRC/$hook" "$DST/$hook"
  chmod +x "$DST/$hook"
  echo "Installed $DST/$hook"
done