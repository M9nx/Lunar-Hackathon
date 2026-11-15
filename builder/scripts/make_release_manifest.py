#!/usr/bin/env python3
"""Write the release manifest: SHA-256 of every file in the candidate, plus the recorded revision.

Outputs (under docs/release/):
  manifest.json      revision record + one entry per file (group, sha256, bytes). Deterministic: no timestamp.
  MANIFEST.sha256    `sha256sum -c` format for the same files.
  RELEASE.md         only the block between the GENERATED markers is rewritten.

The manifest covers code, web (including the witnessed web/replay package), tests, harness scripts, the reference,
the guides, the notebook and the walkthrough, plus the saved Horizons inputs under data/horizons (not in git).
It does NOT cover docs/release/RELEASE.md, manifest.json or MANIFEST.sha256 (a file cannot hold its own hash);
RELEASE.md records the manifest's own SHA-256 instead.

Usage:
  python3 builder/scripts/make_release_manifest.py            # write
  python3 builder/scripts/make_release_manifest.py --check    # exit 1 if the files on disk differ from manifest.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from record_revision import revision_record  # noqa: E402

SKIP_PARTS = ("__pycache__", ".pytest_cache", ".DS_Store")
SKIP_SUFFIX = (".pyc", ".pyo")

# (group, root, glob) in a stable order. data/horizons is the only group that is not in git.
SOURCES = [
    ("replay", "web/replay", "**/*"),
    ("web", "web", "**/*"),
    ("src", "src", "**/*"),
    ("tests", "tests", "**/*"),
    ("scripts", "builder/scripts", "*"),
    ("scripts", ".", "lunar_offline_pack.py"),
    ("reference", "Master-Reference", "**/*"),
    ("docs", "docs", "user-guide.md"),
    ("docs", "docs", "operator-manual.md"),
    ("docs", "docs", "science-and-data-reference.md"),
    ("docs", "docs", "api-reference.md"),
    ("docs", "docs", "engine-reference.md"),
    ("docs", "docs", "data-research.md"),
    ("docs", "docs", "project-progress.md"),
    ("docs", "docs", "real-case-trace.md"),
    ("docs", "docs/notebooks", "*.ipynb"),
    ("docs", "docs/release", "WALKTHROUGH.md"),
    ("docs", "docs/release", "TEAMMATE_CHECKLIST.md"),
    ("inputs", "data/horizons", "*/*/*"),
]
RELEASE = REPO / "docs/release"
BEGIN, END = "<!-- BEGIN GENERATED -->", "<!-- END GENERATED -->"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def collect() -> list[dict]:
    seen: dict[str, dict] = {}
    for group, root, pattern in SOURCES:
        base = REPO / root
        if not base.exists():
            continue
        for path in sorted(base.glob(pattern)):
            if not path.is_file() or path.is_symlink():
                continue
            rel = path.relative_to(REPO).as_posix()
            if any(part in rel for part in SKIP_PARTS) or rel.endswith(SKIP_SUFFIX):
                continue
            if group == "web" and rel.startswith("web/replay/"):
                continue  # already listed under "replay"
            if rel in seen:
                continue
            seen[rel] = {"path": rel, "group": group, "sha256": sha256_file(path), "bytes": path.stat().st_size}
    return sorted(seen.values(), key=lambda item: item["path"])


def build() -> dict:
    rev = revision_record()
    files = collect()
    groups: dict[str, dict] = {}
    for item in files:
        entry = groups.setdefault(item["group"], {"files": 0, "bytes": 0})
        entry["files"] += 1
        entry["bytes"] += item["bytes"]
    for name, entry in groups.items():
        listing = "".join(f"{i['sha256']}  {i['path']}\n" for i in files if i["group"] == name)
        entry["listing_sha256"] = hashlib.sha256(listing.encode()).hexdigest()
    return {
        "schema_version": "release-manifest-1",
        "practice": True,
        "eligible_for_submission_claim": False,
        "revision": {
            key: rev.get(key)
            for key in ("head", "head_short", "branch", "dirty", "label", "witnessed_replay_revision", "code_digest_sha256", "code_paths")
        },
        "groups": groups,
        "files": files,
    }


def render_text(manifest: dict) -> str:
    return json.dumps(manifest, indent=2) + "\n"


def sha_lines(manifest: dict) -> str:
    return "".join(f"{item['sha256']}  {item['path']}\n" for item in manifest["files"])


def generated_block(manifest: dict, manifest_sha: str, sha_list_sha: str) -> str:
    rev = manifest["revision"]
    by_path = {item["path"]: item["sha256"] for item in manifest["files"]}
    key_files = [
        "web/index.html",
        "web/documents.html",
        "web/assets/css/site.css",
        "web/review-candidate/tour.js",
        "web/replay/comparison.json",
        "web/replay/runs/site04-p02-practice.json",
        "web/replay/runs/malapert-practice.json",
        "web/review-candidate/cases/practice-30d/comparison.json",
        "web/review-candidate/cases/practice-30d/runs/site04-p02-practice-30d.json",
        "web/review-candidate/cases/practice-30d/runs/malapert-practice-30d.json",
        "web/review-candidate/cases/practice-jan03-10/comparison.json",
        "docs/notebooks/01_trace_observation_to_interval_total.ipynb",
        "docs/user-guide.md",
        "docs/operator-manual.md",
        "docs/science-and-data-reference.md",
        "docs/api-reference.md",
        "docs/engine-reference.md",
        "docs/data-research.md",
        "docs/project-progress.md",
    ]
    lines = [
        BEGIN,
        "| Item | Value |",
        "| --- | --- |",
        f"| Revision label | `{rev['label']}` (git HEAD `{rev['head']}`, branch `{rev['branch']}`, dirty: {str(rev['dirty']).lower()}) |",
        f"| Code digest (SHA-256 over `src/ tests/ web/ builder/scripts/ Master-Reference/`) | `{rev.get('code_digest_sha256') or 'n/a (clean tree: HEAD alone names the code)'}` |",
        f"| Witnessed replay revision | `{rev['witnessed_replay_revision']}` (`web/replay/` is unchanged by this release) |",
        f"| Files in manifest | {len(manifest['files'])} (" + ", ".join(f"{name} {g['files']}" for name, g in sorted(manifest["groups"].items())) + ") |",
        f"| `docs/release/manifest.json` SHA-256 | `{manifest_sha}` |",
        f"| `docs/release/MANIFEST.sha256` SHA-256 | `{sha_list_sha}` |",
        "",
        "Replay, export, notebook and guide checksums (full list in `MANIFEST.sha256`; check with `sha256sum -c docs/release/MANIFEST.sha256` from the repository root):",
        "",
        "| File | SHA-256 |",
        "| --- | --- |",
    ]
    for path in key_files:
        lines.append(f"| `{path}` | `{by_path.get(path, 'MISSING')}` |")
    lines.append(END)
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", action="store_true", help="compare disk with the existing manifest.json; write nothing")
    args = parser.parse_args()
    RELEASE.mkdir(parents=True, exist_ok=True)
    manifest = build()
    path = RELEASE / "manifest.json"
    if args.check:
        if not path.exists():
            print("no manifest.json")
            return 1
        old = json.loads(path.read_text())
        old_map = {i["path"]: i["sha256"] for i in old["files"]}
        new_map = {i["path"]: i["sha256"] for i in manifest["files"]}
        problems = [f"changed: {p}" for p in sorted(old_map) if p in new_map and old_map[p] != new_map[p]]
        problems += [f"missing: {p}" for p in sorted(old_map) if p not in new_map]
        problems += [f"added: {p}" for p in sorted(new_map) if p not in old_map]
        rev_old, rev_new = old["revision"], manifest["revision"]
        if rev_old.get("code_digest_sha256") != rev_new.get("code_digest_sha256") or rev_old.get("head") != rev_new.get("head"):
            problems.append(f"revision differs: manifest {rev_old.get('label')} {rev_old.get('code_digest_sha256')} vs disk {rev_new.get('label')} {rev_new.get('code_digest_sha256')}")
        print("\n".join(problems) if problems else f"manifest matches disk ({len(new_map)} files)")
        return 1 if problems else 0

    text = render_text(manifest)
    list_text = sha_lines(manifest)
    path.write_text(text)
    (RELEASE / "MANIFEST.sha256").write_text(list_text)
    manifest_sha = hashlib.sha256(text.encode()).hexdigest()
    list_sha = hashlib.sha256(list_text.encode()).hexdigest()
    release = RELEASE / "RELEASE.md"
    if release.exists():
        body = release.read_text()
        block = generated_block(manifest, manifest_sha, list_sha)
        if BEGIN in body and END in body:
            body = re.sub(re.escape(BEGIN) + r".*?" + re.escape(END), lambda _m: block, body, flags=re.S)
            release.write_text(body)
        else:
            print("RELEASE.md has no GENERATED markers; not updated")
    print(f"wrote {path.relative_to(REPO)} ({len(manifest['files'])} files), label {manifest['revision']['label']}, manifest sha256 {manifest_sha}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
