#!/usr/bin/env python3
"""Compare local Lunar-Hackathon-Timeline.xlsx to MASTER_REFERENCE schedule snapshot."""

from __future__ import annotations

import json
import re
import sys
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

BUILDER_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BUILDER_ROOT.parent
JSON_PATH = REPO_ROOT / "Master-Reference" / "MASTER_REFERENCE.json"
DEFAULT_XLSX = Path.home() / "Downloads" / "Lunar-Hackathon-Timeline.xlsx"


def read_timeline_sheet(path: Path) -> tuple[list[str], dict]:
    ns_m = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
    with zipfile.ZipFile(path) as z:
        wb = ET.fromstring(z.read("xl/workbook.xml"))
        sheets = []
        for s in wb.find(f"{ns_m}sheets"):
            rid = s.attrib.get("{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id")
            sheets.append((rid, s.attrib.get("name")))
        rels = ET.fromstring(z.read("xl/_rels/workbook.xml.rels"))
        rid_to_target = {rel.attrib["Id"]: rel.attrib["Target"].lstrip("/") for rel in rels}
        ss: list[str] = []
        if "xl/sharedStrings.xml" in z.namelist():
            root = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in root.findall(f"{ns_m}si"):
                texts = [t.text or "" for t in si.iter(f"{ns_m}t")]
                ss.append("".join(texts))

        def cell_val(c: ET.Element) -> str | None:
            t = c.attrib.get("t")
            v = c.find(f"{ns_m}v")
            if v is None:
                return None
            if t == "s":
                return ss[int(v.text)]
            return v.text

        sheet_names = [name for _, name in sheets]
        target_name = "Tasks" if "Tasks" in sheet_names else "Timeline"
        rid = next(r for r, n in sheets if n == target_name)
        root = ET.fromstring(z.read(rid_to_target[rid]))
        rows: dict[int, dict[str, str | None]] = {}
        for c in root.iter(f"{ns_m}c"):
            ref = c.attrib.get("r")
            if not ref:
                continue
            m = re.match(r"([A-Z]+)(\d+)", ref)
            col, row = m.group(1), int(m.group(2))
            rows.setdefault(row, {})[col] = cell_val(c)
    return sheet_names, rows


def main() -> int:
    xlsx = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_XLSX
    if not xlsx.is_file():
        print(f"MISSING workbook: {xlsx}")
        return 2

    sheet_names, rows = read_timeline_sheet(xlsx)
    has_tasks = "Tasks" in sheet_names
    payload = json.loads(JSON_PATH.read_text(encoding="utf-8"))
    json_tasks = payload["schedule"]["tasks"]
    json_ids = [t["task_id"] for t in json_tasks]

    print(f"workbook={xlsx}")
    print(f"sheets={sheet_names}")
    print(f"has_tasks_tab={has_tasks}")
    print(f"json_task_count={len(json_ids)}")

    if has_tasks:
        xlsx_ids = []
        for row in sorted(rows):
            joined = " ".join(str(v) for v in rows[row].values() if v)
            for token in joined.split():
                if re.fullmatch(r"M\d+\.\d+", token) or token == "Rest":
                    xlsx_ids.append(token)
        print(f"xlsx_task_tokens={len(xlsx_ids)}")
        if set(json_ids) == set(xlsx_ids):
            print("result=MATCH detailed task IDs")
        else:
            print("result=DIFFER use JSON schedule snapshot")
    else:
        print("result=NO_TASKS_TAB use JSON schedule snapshot (M0.1-M6.5)")
        phase_rows = []
        for row in sorted(rows):
            vals = [rows[row][c] for c in sorted(rows[row], key=lambda x: (len(x), x))]
            if vals and vals[0] in {"M0", "M1", "M2", "M3", "M4", "M5", "M6"}:
                phase_rows.append(vals)
        print("workbook_phase_rows:")
        for pr in phase_rows:
            print(" ", pr[:6])
    return 0


if __name__ == "__main__":
    sys.exit(main())