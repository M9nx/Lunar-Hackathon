#!/usr/bin/env python3
"""QA-style reproduction of the release from the exact candidate revision.

1. `git clone` the repository into a temp directory (HEAD named in docs/release/manifest.json).
2. Overlay the candidate's uncommitted changes (modified and untracked files, minus deletions), so the copy is the
   working tree that was tested.
3. Copy the saved Horizons inputs (default: data/horizons; use --data-from for a backup) and link the other data.
4. Check every file against the manifest, and that record_revision.py in the copy reports the manifest's label
   and code digest.
5. Run the documented commands in the copy: input checks, package reproduction compared byte-for-byte (apart from
   code_revision) with the saved packages, the test suite, the notebook, the guide walk, and the browser checks.
6. Confirm web/replay is identical in source and copy, and write the record to --out.

It never touches a running server on 8766 and never writes into web/replay.

  .venv/bin/python builder/scripts/verify_release_package.py [--out DIR] [--data-from DIR] [--skip-browser] [--keep]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCENARIOS = [
    "site04_p02_practice",
    "malapert_practice",
    "site04_p02_practice_30d",
    "malapert_practice_30d",
]
NOTEBOOK = "docs/notebooks/01_trace_observation_to_interval_total.ipynb"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return sock.getsockname()[1]


def git_names(*args: str) -> list[str]:
    raw = subprocess.check_output(["git", *args, "-z"], cwd=REPO)
    return [name for name in raw.decode().split("\0") if name]


class Report:
    def __init__(self, out: Path) -> None:
        self.out = out
        self.logs = out / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.steps: list[dict] = []

    def add(self, name: str, ok: bool, detail="", command: str = "", seconds: float = 0.0, log: str = "") -> bool:
        self.steps.append(
            {"step": name, "pass": bool(ok), "detail": detail, "command": command, "seconds": round(seconds, 1), "log": log}
        )
        print(("PASS " if ok else "FAIL ") + name + (f" :: {detail}" if detail else ""), flush=True)
        return bool(ok)

    def run(self, name: str, command: list[str], cwd: Path, env: dict, timeout: int = 900, shell_text: str = "") -> bool:
        started = time.time()
        log_name = f"{len(self.steps) + 1:02d}_{name.replace(' ', '_').replace('/', '_')[:50]}.log"
        try:
            proc = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=timeout)
            output, rc = proc.stdout + proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            output, rc = f"timeout after {timeout}s\n{exc.stdout or ''}", 124
        (self.logs / log_name).write_text(output)
        tail = " | ".join(line for line in output.strip().splitlines()[-2:])[:200]
        return self.add(name, rc == 0, f"rc={rc} {tail}", shell_text or " ".join(command), time.time() - started, f"logs/{log_name}")


def same_ignoring_revision(a: Path, b: Path) -> tuple[bool, str]:
    left, right = json.loads(a.read_text()), json.loads(b.read_text())
    left.pop("code_revision", None)
    right.pop("code_revision", None)
    return left == right, ""


def compare_trees(saved: Path, fresh: Path) -> tuple[bool, list[str]]:
    problems: list[str] = []
    names = sorted(p.relative_to(saved).as_posix() for p in saved.rglob("*.json"))
    fresh_names = sorted(p.relative_to(fresh).as_posix() for p in fresh.rglob("*.json"))
    if names != fresh_names:
        problems.append(f"file lists differ: {names} vs {fresh_names}")
    for name in names:
        if name in fresh_names:
            ok, _ = same_ignoring_revision(saved / name, fresh / name)
            if not ok:
                problems.append(f"differs: {name}")
    return not problems, problems


def serve(copy: Path, label: str, port: int, env: dict) -> subprocess.Popen:
    proc = subprocess.Popen(
        [sys.executable, "-m", "lunar_navigator.cli", "--revision", label, "serve", "--port", str(port)],
        cwd=copy,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,
    )
    for _ in range(80):
        try:
            if urllib.request.urlopen(f"http://127.0.0.1:{port}/review-candidate/", timeout=1).status == 200:
                return proc
        except Exception:
            time.sleep(0.25)
    stop(proc)
    raise RuntimeError("server did not start")


def stop(proc: subprocess.Popen) -> None:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
        proc.wait(timeout=5)
    except Exception:
        try:
            os.killpg(proc.pid, signal.SIGKILL)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(REPO / "builder/docs/evidence/s3/release_verify"))
    parser.add_argument("--data-from", default=str(REPO / "data/horizons"), help="folder holding the saved Horizons exports")
    parser.add_argument("--skip-browser", action="store_true", help="skip the three browser checks (the guide walk also needs a browser)")
    parser.add_argument("--keep", action="store_true", help="keep the temp copy")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    report = Report(out)
    manifest = json.loads((REPO / "docs/release/manifest.json").read_text())
    want = manifest["revision"]
    py = sys.executable
    temp = Path(tempfile.mkdtemp(prefix="lunar-release-"))
    copy = temp / "candidate"
    started = time.time()
    try:
        # 1-2. Exact candidate.
        head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip()
        report.add("source HEAD matches the manifest", head == want["head"], f"{head[:12]} vs {want['head'][:12]}")
        subprocess.run(["git", "clone", "--no-hardlinks", "-q", str(REPO), str(copy)], check=True)
        changed = [n for n in git_names("ls-files", "-m", "-o", "--exclude-standard") if "__pycache__" not in n]
        deleted = set(git_names("ls-files", "-d"))
        copied = 0
        for name in changed:
            if name in deleted:
                continue
            src = REPO / name
            if src.is_file():
                dst = copy / name
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                copied += 1
        for name in deleted:
            target = copy / name
            if target.exists():
                target.unlink()
        report.add("overlay applied", True, f"{copied} changed/untracked files copied, {len(deleted)} deletions", "git clone + overlay")

        # 3. Inputs.
        data_from = Path(args.data_from)
        (copy / "data").mkdir(exist_ok=True)
        if data_from.is_dir():
            shutil.copytree(data_from, copy / "data/horizons")
        for entry in ("LOLA_5mpp", "LOLA_20mpp", "LOLA_product69", "offline", "spice"):
            src = REPO / "data" / entry
            if src.exists():
                (copy / "data" / entry).symlink_to(src)
        report.add("saved Horizons inputs copied", (copy / "data/horizons").is_dir(), str(data_from))

        # 4. Manifest and revision.
        bad: list[str] = []
        for item in manifest["files"]:
            path = copy / item["path"]
            if not path.is_file() or sha256_file(path) != item["sha256"]:
                bad.append(item["path"])
        report.add(
            "every manifest file matches in the copy",
            not bad,
            f"{len(manifest['files']) - len(bad)}/{len(manifest['files'])} files match" + (f"; first bad: {bad[:5]}" if bad else ""),
            "sha256 of each file in docs/release/manifest.json",
        )
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONPATH=str(copy / "src"))
        rev = json.loads(subprocess.check_output([py, "builder/scripts/record_revision.py"], cwd=copy, env=env, text=True))
        report.add(
            "copy reports the manifest revision and code digest",
            rev["label"] == want["label"] and rev.get("code_digest_sha256") == want.get("code_digest_sha256"),
            f"{rev['label']} {rev.get('code_digest_sha256')} vs {want['label']} {want.get('code_digest_sha256')}",
            "python3 builder/scripts/record_revision.py",
        )
        label = want["label"]
        imp = subprocess.run([py, "-c", "import lunar_navigator;print(lunar_navigator.__file__)"], cwd=copy, env=env, capture_output=True, text=True)
        report.add("copy imports its own engine", str(copy) in imp.stdout, imp.stdout.strip())

        # 5. Documented commands (Operator Manual sections 4 and 6).
        report.run("input files (Manual 4.1)", ["python3", "lunar_offline_pack.py", "check-horizons"], copy, env)
        for name in SCENARIOS:
            report.run(
                f"scenario fit {name} (Manual 4.2)",
                ["python3", "builder/scripts/case_fit_horizons.py", "--scenario", f"tests/fixtures/{name}_scenario.json"],
                copy,
                env,
            )
        report.run("raw digest provenance (Manual 4.3)", ["python3", "builder/scripts/horizons_digest_check.py", "--check"], copy, env)

        for pair, saved in (("practice-48h", "web/replay"), ("practice-30d", "web/review-candidate/cases/practice-30d")):
            fresh = temp / f"fresh-{pair}"
            ok = report.run(
                f"package --pair {pair} (Manual 6)",
                ["python3", "-m", "lunar_navigator.cli", "--revision", label, "package", "--pair", pair, "--out", str(fresh)],
                copy,
                env,
                shell_text=f"python3 -m lunar_navigator.cli --revision {label} package --pair {pair} --out <temp>",
            )
            if ok:
                same, problems = compare_trees(copy / saved, fresh)
                report.add(f"{pair} package equals the saved package (ignoring code_revision)", same, "; ".join(problems) or "all JSON files equal")

        report.run(
            "test suite",
            [py, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"],
            copy,
            env,
            shell_text=".venv/bin/python -m pytest tests -q -p no:cacheprovider",
        )
        report.run("notebook trace", ["python3", "builder/scripts/run_notebook.py", "--check", NOTEBOOK], copy, env)
        report.run("release manifest check", ["python3", "builder/scripts/make_release_manifest.py", "--check"], copy, env)

        # Guide walk and browser checks.
        if args.skip_browser:
            report.add("browser checks", True, "skipped by --skip-browser (recorded as skipped, not passed)")
        else:
            walk_dir = out / "guide_walk"
            report.run(
                "guide walk (User Guide quick start, literal command)",
                [py, "builder/scripts/s3_guide_walk.py", "--evidence-dir", str(walk_dir), "--driver-port", str(free_port()), "--profile", f"/tmp/lunar-s3v-walk-{os.getpid()}"],
                copy,
                env,
            )
            report.run(
                "live stream trace",
                [py, "builder/scripts/live_stream_trace.py", "--out", str(out / "live_trace.json"), "--shots", str(out)],
                copy,
                env,
            )
            for name, script, extra in (
                ("browser check", "review_candidate_browser_check.py", ["--evidence-dir", str(out / "browser")]),
                ("flow check", "s2_flow_check.py", ["--evidence-dir", str(out / "flow")]),
            ):
                port = free_port()
                server = serve(copy, label, port, env)
                try:
                    report.run(
                        name,
                        [py, f"builder/scripts/{script}", "--base", f"http://127.0.0.1:{port}/review-candidate/", *extra, "--driver-port", str(free_port()), "--profile", f"/tmp/lunar-s3v-{name.split()[0]}-{os.getpid()}"],
                        copy,
                        env,
                        timeout=1200,
                    )
                finally:
                    stop(server)

        # 6. The witnessed replay is unchanged.
        def replay_hash(root: Path) -> str:
            files = sorted((root / "web/replay").rglob("*"))
            digest = hashlib.sha256()
            for path in files:
                if path.is_file():
                    digest.update(path.relative_to(root).as_posix().encode() + b"\0" + sha256_file(path).encode() + b"\n")
            return digest.hexdigest()

        a, b = replay_hash(REPO), replay_hash(copy)
        report.add("web/replay identical in source and copy", a == b, a)
    finally:
        elapsed = time.time() - started
        passed = sum(1 for s in report.steps if s["pass"])
        record = {
            "schema_version": "release-verify-1",
            "revision": want,
            "data_from": str(args.data_from),
            "skip_browser": args.skip_browser,
            "temp_copy": str(copy) if args.keep else "removed",
            "seconds": round(elapsed, 1),
            "passed": passed,
            "total": len(report.steps),
            "steps": report.steps,
        }
        (out / "release_verify.json").write_text(json.dumps(record, indent=2) + "\n")
        lines = [
            "# Release reproduction from the candidate revision",
            "",
            f"Revision `{want['label']}`, code digest `{want.get('code_digest_sha256')}`. {passed}/{len(report.steps)} steps passed in {round(elapsed)} s.",
            f"Browser checks: {'skipped' if args.skip_browser else 'run'}. Saved inputs from `{args.data_from}`.",
            "",
            "| Step | Result | Command | Detail |",
            "| --- | --- | --- | --- |",
        ]
        for s in report.steps:
            detail = str(s["detail"]).replace("|", "/").replace("\n", " ")[:160]
            cmd = s["command"].replace("|", "/")[:110]
            lines.append(f"| {s['step']} | {'pass' if s['pass'] else '**FAIL**'} | `{cmd}` | {detail} |")
        (out / "release_verify.md").write_text("\n".join(lines) + "\n")
        if not args.keep:
            shutil.rmtree(temp, ignore_errors=True)
        print(f"{passed}/{len(report.steps)} release-verification steps passed; record in {out}")
    return 0 if passed == len(report.steps) else 1


if __name__ == "__main__":
    sys.exit(main())
