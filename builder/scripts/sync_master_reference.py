#!/usr/bin/env python3
"""Sync MASTER_REFERENCE.md and .html from MASTER_REFERENCE.json (rev 0.5)."""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

try:
    import markdown
except ImportError as exc:  # pragma: no cover
    raise SystemExit("python-markdown is required to regenerate HTML") from exc

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent
REF_DIR = REPO_ROOT / "Master-Reference"
JSON_PATH = REF_DIR / "MASTER_REFERENCE.json"
MD_PATH = REF_DIR / "MASTER_REFERENCE.md"
HTML_PATH = REF_DIR / "MASTER_REFERENCE.html"

HTML_HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Lunar Landing Site Navigator — Master Reference</title>
<style>
:root {color-scheme: light; --ink:#18273a; --muted:#52667a; --line:#dce5ec; --bg:#f7f9fc; --link:#135b8a}
* {box-sizing:border-box} body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.63 system-ui,sans-serif}
main{margin:0 auto;max-width:1040px;padding:3rem clamp(1rem,4.5vw,3.8rem) 4rem;background:white}
h1,h2,h3{line-height:1.18;text-wrap:balance}
h1{font-size:clamp(2rem,5vw,3.6rem);letter-spacing:-.043em;margin:0 0 1.3rem;max-width:18ch}
h2{font-size:clamp(1.52rem,3.3vw,2.18rem);letter-spacing:-.025em;border-top:1px solid var(--line);padding-top:1.1rem;margin:1.4rem 0 .9rem}
h3{font-size:1.3rem;margin:1.55rem 0 .6rem}
a{color:var(--link);text-underline-offset:.2em;overflow-wrap:anywhere}
a:focus-visible{outline:2px solid var(--link);outline-offset:2px}
a[id]{display:block;scroll-margin-top:1.3rem}
p{margin:.7rem 0 1rem}
p:has(>a[id]:only-child){margin:0}
nav.jump{border:1px solid var(--line);padding:.85rem 1rem;background:var(--bg);margin-bottom:1rem}
nav.jump a{display:inline-block;margin:.1rem .35rem}
.table-scroll{overflow:auto;margin:1rem 0 1.35rem}
table{border-collapse:collapse;width:100%;font-size:.94rem;line-height:1.48}
th,td{padding:.55rem .65rem;text-align:left;vertical-align:top;border-bottom:1px solid var(--line)}
thead{background:#eaf1f7} tbody tr:nth-child(even){background:#f7f9fc}
code{font: .91em/1.4 ui-monospace,monospace;color:#20405e}
pre{background:#f1f5f9;padding:1rem;border:1px solid var(--line);overflow:auto;border-radius:.25rem}
figure{margin:1.3rem 0 1.8rem}
.science-figure{border:1px solid var(--line);padding:.75rem;break-inside:avoid}
img{display:block;max-width:100%;height:auto;margin:auto}
@media(max-width:620px){main{padding-top:2rem}table{min-width:560px}}
@media print{body,main{background:#fff}main{max-width:none;padding:0}h2,h3{break-after:avoid}.table-scroll{overflow:visible}}
</style>
</head>
<body><main>
"""


def build_markdown(payload: dict) -> str:
    doc = payload["document"]
    chunks = [doc.get("preamble_markdown", "").rstrip()]
    for section in doc.get("sections", []):
        text = (section.get("markdown") or "").strip()
        if text:
            chunks.append(text)
    return "\n\n".join(chunks).strip() + "\n"


def slugify_heading(text: str) -> str:
    text = re.sub(r"<[^>]+>", "", text)
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text).strip("-")


def render_html(md_text: str) -> str:
    body = markdown.markdown(
        md_text,
        extensions=["tables", "fenced_code", "sane_lists", "nl2br"],
        output_format="html5",
    )
    body = re.sub(
        r'<a id="([^"]+)"></a>',
        r'<a id="\1"></a>',
        body,
    )
    return HTML_HEAD + body + "\n</main></body></html>\n"


def main() -> int:
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    md_text = build_markdown(payload)
    md_sha = hashlib.sha256(md_text.encode("utf-8")).hexdigest()

    MD_PATH.write_text(md_text, encoding="utf-8")
    HTML_PATH.write_text(render_html(md_text), encoding="utf-8")

    doc = payload["document"]
    doc["markdown_sha256"] = md_sha
    payload["document"] = doc
    JSON_PATH.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    on_disk = hashlib.sha256(MD_PATH.read_bytes()).hexdigest()
    print(f"reference_revision={doc.get('reference_revision')}")
    print(f"markdown_sha256={md_sha}")
    print(f"md_bytes={len(md_text.encode())}")
    print(f"sha_verify={'OK' if on_disk == md_sha == doc['markdown_sha256'] else 'FAIL'}")
    return 0 if on_disk == md_sha else 1


if __name__ == "__main__":
    sys.exit(main())