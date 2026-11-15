#!/usr/bin/env python3
"""Stage public lunar data on a connected machine, then verify it offline.

Python 3.10+ and curl are required. Run with --help for download profiles,
Horizons exports, and a Python wheel cache for the demo laptop.
"""

import argparse
import csv
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode

PGDA = "https://pgda.gsfc.nasa.gov"
NAIF = "https://naif.jpl.nasa.gov/pub/naif/generic_kernels"
MIT_PDS = "https://imbrium.mit.edu/EXTRAS/ILLUMINATION/IMG"
PDS_SKY = "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/extras/illumination/release_2014/img"
NASA_MEDIA = "https://assets.science.nasa.gov/content/dam/science"
HORIZONS = "https://ssd.jpl.nasa.gov/api/horizons.api"
HORIZONS_DOCS = "https://ssd-api.jpl.nasa.gov/doc/horizons.html"
HORIZONS_MANUAL = "https://ssd.jpl.nasa.gov/horizons/manual.html"
PRACTICE_MALAPERT = "https://science.nasa.gov/wp-content/uploads/2023/04/LRO_PSS_Talk.pptxTAGGED.pdf"
ORGANIZER = "https://github.com/nasa/spaceapps/discussions/1827"
PACKS = {
    "core": "Product 90 south-polar 240 m DEM, polar mosaic, local Plotly, source notes",
    "terrain": "Product 90 80 m DEM and Product 78 Site04/Shackleton and Site23/Malapert 5 m tiles",
    "candidates": "Thirteen additional Product 78 site elevation grids for alternate landing locations",
    "visibility": "Product 69 Earth, Sun, permanent shadow and sky-view rasters with PDS labels",
    "spice": "NAIF DE421 ephemeris, lunar orientation, frame, constants and leap-second kernels",
    "visuals": "Earthrise, Solar Dynamics Observatory Sun image, JPL photo, Artemis region map and hillshade",
    "upgrade": "Product 90 20 m DEM, slope, error, effective-resolution and observation-count rasters",
}
EARTH69 = "AVGVISIB_65S_240M_201608_EARTH"
PYTHON_PACKAGES = ("numpy", "rasterio", "pyproj", "spiceypy", "fastapi", "uvicorn", "pytest")


@dataclass(frozen=True)
class Asset:
    pack: str
    path: str
    url: str
    source: str
    use: str
    size: int = 0
    sha256: str = ""
    credit: str = ""


def p90(pack, file, size, use, sha=""):
    path = f"LOLA_20mpp/{file}.TIF"
    return Asset(pack, path, f"{PGDA}/data/{path}", f"{PGDA}/products/90", use, size, sha,
                 "NASA Goddard PGDA / LOLA")


def p78(site, kind, size, use, pack="terrain"):
    path = f"LOLA_5mpp/{site}/{site}_final_adj_5mpp_{kind}.tif"
    return Asset(pack, path, f"{PGDA}/data/{path}", f"{PGDA}/products/78", use, size,
                 credit="NASA Goddard PGDA / LOLA")


def p69(name, size, use, sha=""):
    base = f"{PGDA}/products/69"
    label = f"{MIT_PDS}/{name}.LBL" if name != "SKYV_65S_240M" else f"{PDS_SKY}/skyv_65s_240m.lbl"
    return (
        Asset("visibility", f"LOLA_product69/{name}.TIF", f"{PGDA}/data/MoonIllumination/{name}.TIF",
              base, use, size, sha, "NASA Goddard PGDA / LOLA"),
        Asset("visibility", f"LOLA_product69/{name.lower()}.lbl", label, base,
              "PDS source label. Review the GeoTIFF's own scale, offset, and masks as well.",
              credit="NASA PDS / LOLA"),
    )


def kernel(path, size, use):
    return Asset("spice", f"spice/de421/{Path(path).name}", f"{NAIF}/{path}",
                 "https://naif.jpl.nasa.gov/naif/data_generic.html", use, size,
                 credit="NASA/JPL NAIF")


ASSETS = [
    p90("core", "LDEM_60S_240MPP_ADJ", 218961039, "Regional elevation, 60°S to pole",
        "3f9663257b63022f2b0d5a623482ff3cadddceb91594a4e4ca14a94d8cec8b34"),
    Asset("core", "offline/assets/PIA13523-south-pole.jpg",
          f"{NASA_MEDIA}/psd/photojournal/pia/pia13/pia13523/PIA13523.jpg",
          "https://science.nasa.gov/photojournal/the-lunar-south-pole/",
          "Context image for UI and judging", 420759, credit="NASA / GSFC / Arizona State University"),
    Asset("core", "offline/vendor/plotly-3.0.1.min.js", "https://cdn.plot.ly/plotly-3.0.1.min.js",
          "https://github.com/plotly/plotly.js/tree/v3.0.1", "Optional locally served chart library",
          4653932, credit="Plotly Technologies Inc., MIT"),
    Asset("core", "offline/vendor/plotly-LICENSE.txt",
          "https://raw.githubusercontent.com/plotly/plotly.js/v3.0.1/LICENSE",
          "https://github.com/plotly/plotly.js/blob/v3.0.1/LICENSE", "Redistribution terms", 1086),
    Asset("core", "offline/reference/pgda-product-90.html", f"{PGDA}/products/90",
          f"{PGDA}/products/90", "Regional DEM release notes"),
    Asset("core", "offline/reference/horizons-api.html", HORIZONS_DOCS, HORIZONS_DOCS,
          "Observer query parameters and response format"),
    Asset("core", "offline/reference/horizons-manual.html", HORIZONS_MANUAL,
          HORIZONS_MANUAL, "Horizons observer conventions and reference frames"),
    p90("terrain", "LDEM_80S_80MPP_ADJ", 189158392, "Regional elevation, 80°S to pole",
        "82030dcbdd7c4bb0c7d858e9b4b293b9f2cda5a543ba31ec0f42784bd6beee5a"),
    p78("Site04", "surf", 40980806, "Site04 5 m surface elevation"),
    p78("Site04", "ldec", 40980740, "Site04 laser-shot counts"),
    p78("Site04", "toterr", 40980808, "Site04 elevation uncertainty"),
    p78("Site23", "surf", 70586804, "Site23 Malapert Massif 5 m surface elevation"),
    p78("Site23", "ldec", 70586742, "Site23 laser-shot counts"),
    p78("Site23", "toterr", 70586811, "Site23 elevation uncertainty"),
    Asset("terrain", "LOLA_5mpp/Site04/Site04_ROIs.tgz",
          f"{PGDA}/data/LOLA_5mpp/Site04/Site04_ROIs.tgz", f"{PGDA}/products/78",
          "Site04 regions of interest, shapefile archive", 1712),
    Asset("terrain", "offline/reference/pgda-product-78.html", f"{PGDA}/products/78",
          f"{PGDA}/products/78", "Local DEM release notes and site index"),
    Asset("terrain", "offline/reference/pgda-product-78-readme", f"{PGDA}/data/LOLA_5mpp/README",
          f"{PGDA}/products/78", "Product 78 README supplied with the data"),
    *[p78(site, "surf", size, place, "candidates") for site, size, place in (
        ("Site01", 40980810, "Connecting Ridge"),
        ("Site06", 64025603, "Nobile Rim 1"),
        ("Site07", 40980808, "Peak near Shackleton"),
        ("Site11", 40980806, "de Gerlache Rim"),
        ("Site20", 40980802, "Leibnitz Beta Plateau"),
        ("Site20v2", 108192905, "Leibnitz Beta Plateau, extended"),
        ("Site42", 64025611, "de Gerlache–Kocher Massif"),
        ("Haworth", 142123767, "Haworth"),
        ("Shoemaker", 64025605, "Shoemaker"),
        ("DM1", 64033681, "Amundsen Rim"),
        ("DM2", 64025607, "Nobile Rim 2"),
        ("SL2", 64025605, "de Gerlache Rim alternate"),
        ("SL3", 64025611, "Connecting Ridge Extension"),
    )],
    *p69(EARTH69, 22963503, "Long-term fraction with any part of Earth's disc visible",
         "8a6d5fa8079c83e2159adf58ce33cd1cd9c09be6c19023bf5b6cc304f51568b7"),
    *p69("AVGVISIB_65S_240M_201608", 60394652, "Long-term solar illumination"),
    *p69("LPSR_65S_240M_201608", 582074, "Permanent shadow context"),
    *p69("SKYV_65S_240M", 62718743, "Sky-view fraction, separate metric"),
    Asset("visibility", "offline/reference/pgda-product-69.html", f"{PGDA}/products/69",
          f"{PGDA}/products/69", "Illumination model, visibility definitions and averaging period"),
    kernel("spk/planets/a_old_versions/de421.bsp", 16790528, "Planetary and lunar positions"),
    kernel("pck/moon_pa_de421_1900-2050.bpc", 1770496, "Lunar orientation, check date coverage"),
    kernel("pck/pck00010.tpc", 126143, "Body radii and constants"),
    kernel("fk/satellites/moon_080317.tf", 21437, "DE421 lunar frame definitions"),
    kernel("lsk/naif0012.tls", 5257, "Pinned leap-second kernel for practice reproduction"),
    Asset("visuals", "offline/assets/apollo8-earthrise.jpg",
          f"{NASA_MEDIA}/psd/solar/2023/09/a/as08-14-2383.jpg",
          "https://science.nasa.gov/resource/apollo-8s-iconic-earthrise/",
          "Presentation imagery", 494374, credit="NASA / Bill Anders"),
    Asset("visuals", "offline/assets/PIA26681-sun.jpg",
          f"{NASA_MEDIA}/psd/photojournal/pia/pia26/pia26681/PIA26681.jpg",
          "https://science.nasa.gov/photojournal/image-of-sun-from-nasas-solar-dynamics-observatory/",
          "Illustrative Sun imagery", 1316280, credit="NASA / Solar Dynamics Observatory, see source for full credit"),
    Asset("visuals", "offline/assets/PIA22555-jpl-campus.jpg",
          "https://d2pn8kiwq2w21t.cloudfront.net/images/jpegPIA22555.width-1024.jpg",
          "https://www.jpl.nasa.gov/images/pia22555-jet-propulsion-laboratory-nestled-in-hillside/",
          "Presentation imagery", 135273, credit="NASA/JPL-Caltech"),
    Asset("visuals", "offline/assets/apollo-lunar-module.glb",
          f"{NASA_MEDIA}/cds/3d/resources/model/apollo-lunar-module/Apollo%20Lunar%20Module.glb",
          "https://science.nasa.gov/3d-resources/apollo-lunar-module/",
          "Optional UI model", 716840, credit="NASA / Michael D. Carbajal, see source for full credit"),
    Asset("visuals", "offline/reference/artemis-candidate-regions.pdf",
          "https://science.nasa.gov/wp-content/uploads/2024/09/1-2-artemis-sato-2024-1.pdf",
          "https://science.nasa.gov/wp-content/uploads/2024/09/1-2-artemis-sato-2024-1.pdf",
          "Region context. Choose and document a precise point before modeling.", 5343811, credit="NASA"),
    p90("visuals", "LDEM_60S_240MPP_ADJ_HILL", 97015883, "Hillshade for display"),
    p90("upgrade", "LDEM_80S_20MPP_ADJ", 2696082051, "Finer regional elevation grid"),
    p90("upgrade", "LDSM_60S_240MPP_ADJ", 258884830, "Regional slope layer"),
    p90("upgrade", "LDEC_80S_80MPP_ADJ", 115657642, "Laser observation counts"),
    p90("upgrade", "LDEM_80S_80MPP_ADJ_EFFRES", 250228467, "Effective resolution layer"),
    p90("upgrade", "LDEM_80S_80MPP_ADJ_ERR", 254808965, "Surface-height uncertainty"),
]

REFERENCES = {
    "Challenge resources": "https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/?tab=resources",
    "Organizer guidance": ORGANIZER,
    "QuickMap": "https://quickmap.lroc.asu.edu/",
    "Moon Trek": "https://trek.nasa.gov/moon/",
    "Moon Trek layer services": "https://trek.nasa.gov/tiles/apidoc/index.html",
    "CSA Moon Exploration": "https://www.asc-csa.gc.ca/eng/astronomy/moon-exploration/",
    "Horizons web export": "https://ssd.jpl.nasa.gov/horizons/",
    "Horizons manual": HORIZONS_MANUAL,
    "JPL API fair use": "https://ssd-api.jpl.nasa.gov/doc/",
    "NASA media credits and use": "https://www.nasa.gov/nasa-brand-center/images-and-media/",
    "CGI Moon Kit, optional 3D texture": "https://svs.gsfc.nasa.gov/4720/",
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=path.parent, delete=False) as tmp:
        name = Path(tmp.name)
        try:
            json.dump(value, tmp, indent=2, ensure_ascii=False)
            tmp.write("\n")
        except BaseException:
            name.unlink(missing_ok=True)
            raise
    os.replace(name, path)


def sha(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify(path, asset, receipt=None):
    size = path.stat().st_size
    if not size or (asset.size and size != asset.size):
        raise ValueError(f"size {size} bytes, expected {asset.size or 'a non-empty file'}")
    with path.open("rb") as stream:
        prefix = stream.read(4096)
    ext = Path(asset.path).suffix.lower()
    signatures = {
        ".tif": (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"),
        ".jpg": (b"\xff\xd8\xff",), ".pdf": (b"%PDF-",), ".tgz": (b"\x1f\x8b",), ".glb": (b"glTF",),
        ".bsp": (b"DAF/SPK",), ".bpc": (b"DAF/PCK",), ".tpc": (b"KPL/PCK",),
        ".tf": (b"KPL/FK",), ".tls": (b"KPL/LSK",),
    }
    if ext in signatures and not prefix.startswith(signatures[ext]):
        raise ValueError(f"unexpected file header for {ext}")
    if ext == ".html" and b"<html" not in prefix.lower():
        raise ValueError("expected an HTML document")
    if ext == ".lbl" and b"PDS_VERSION_ID" not in prefix:
        raise ValueError("expected a PDS label")
    if ext == ".js" and b"plotly.js" not in prefix.lower():
        raise ValueError("expected the Plotly distribution")
    if ext == ".txt" and b"MIT License" not in prefix:
        raise ValueError("expected the MIT license")
    actual = sha(path)
    expected = asset.sha256 or (receipt or {}).get("downloaded_sha256")
    if expected and actual != expected:
        raise ValueError(f"SHA-256 mismatch: {actual}")
    return {**asdict(asset), "downloaded_bytes": size, "downloaded_sha256": actual}


def curl(url, path, *, resume=False, agent=None):
    cmd = ["curl", "--fail", "--location", "--show-error", "--progress-bar",
           "--proto", "=https", "--proto-redir", "=https", "--connect-timeout", "20",
           "--speed-limit", "1024", "--speed-time", "60", "--retry", "2",
           "--retry-delay", "5", "--output", str(path)]
    if resume:
        cmd += ["--continue-at", "-"]
    if agent:
        cmd += ["--user-agent", agent, "--max-time", "120", "--retry-delay", "0"]
    return subprocess.run([*cmd, "--", url], check=False).returncode


def download(root, asset, receipt):
    path = root / asset.path
    if path.exists():
        return verify(path, asset, receipt)
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    if partial.exists() and asset.size and partial.stat().st_size >= asset.size:
        try:
            metadata = verify(partial, asset, receipt)
        except ValueError:
            partial.unlink()
        else:
            os.replace(partial, path)
            return metadata
    code = curl(asset.url, partial, resume=partial.exists())
    if code in (33, 36):  # Range or resume rejected. Retry this file from byte zero.
        partial.unlink(missing_ok=True)
        code = curl(asset.url, partial)
    if code:
        raise RuntimeError(f"curl exited {code}. Rerun to resume any partial transfer.")
    try:
        metadata = verify(partial, asset, receipt)
    except ValueError:
        # A successful transfer with invalid contents should start afresh next time.
        partial.unlink()
        raise
    os.replace(partial, path)
    return metadata


def selected(packs):
    return ASSETS if "all" in packs else [asset for asset in ASSETS if asset.pack in packs]


def parse_pack(value):
    if value not in PACKS and value != "all":
        raise argparse.ArgumentTypeError("choose " + ", ".join((*PACKS, "all")))
    return value


def plan(packs):
    selection = selected(packs)
    for name, description in PACKS.items():
        files = [a for a in selection if a.pack == name]
        if not files:
            continue
        total = sum(a.size for a in files)
        print(f"\n{name}: {description} ({total / 1_000_000:.1f} MB known)")
        for a in files:
            size = f"{a.size / 1_000_000:.2f} MB" if a.size else "size varies"
            print(f"  {a.path:<69} {size:>11}  {a.url}")
    print(f"\n{len(selection)} files, {sum(a.size for a in selection) / 1_000_000:.1f} MB of known download sizes.")


def assets_command(root, packs, fetch, open_dem=False):
    if open_dem:
        try:
            import rasterio
        except ImportError as exc:
            raise RuntimeError("--open-dem requires Rasterio in this Python environment") from exc
    manifest = root / "offline" / "manifest.json"
    saved = json.loads(manifest.read_text(encoding="utf-8")) if manifest.exists() else {}
    receipts = saved.get("files", {})
    failures = []
    for asset in selected(packs):
        file = root / asset.path
        try:
            if fetch and not file.exists():
                print(f"GET  {asset.path}", flush=True)
            receipts[asset.path] = (download(root, asset, receipts.get(asset.path)) if fetch
                                    else verify(file, asset, receipts.get(asset.path)))
            if open_dem and file.suffix.lower() == ".tif":
                with rasterio.Env(PROJ_NETWORK="OFF"), rasterio.open(file) as dataset:
                    window = rasterio.windows.Window(dataset.width // 2, dataset.height // 2, 1, 1)
                    dataset.read(1, window=window, masked=True)
                    print(f"     {dataset.width} × {dataset.height}, {dataset.dtypes[0]}, NoData={dataset.nodata}")
            print(f" OK  {asset.path}", flush=True)
        except (OSError, ValueError, RuntimeError) as exc:
            print(f"FAIL {asset.path}: {exc}", file=sys.stderr)
            failures.append(asset.path)
    if fetch:
        write_json(manifest, {"files": receipts, "references": REFERENCES})
        print(f"\nSource URLs, credits and SHA-256: {manifest}")
    if failures:
        print(f"{len(failures)} selected files failed. Move aside any invalid complete files before retrying.",
              file=sys.stderr)
    return bool(failures)


def parse_site(value):
    fields = value.split(",")
    if len(fields) != 4:
        raise argparse.ArgumentTypeError("use NAME,LON,LAT,ALT_KM")
    name, *coords = fields
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,47}", name):
        raise argparse.ArgumentTypeError("site name must use letters, digits, underscores or hyphens")
    try:
        lon, lat, alt = map(float, coords)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("longitude, latitude and altitude must be numbers") from exc
    if not all(map(math.isfinite, (lon, lat, alt))) or not (-360 < lon < 360 and -90 < lat < 90):
        raise argparse.ArgumentTypeError("use finite east-positive longitude and latitude strictly between the poles")
    return name, lon, lat, alt


def parse_date(value):
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise argparse.ArgumentTypeError("use YYYY-MM-DD or YYYY-MM-DDTHH:MMZ") from exc
    if dt.tzinfo is not None and dt.utcoffset().total_seconds() != 0:
        raise argparse.ArgumentTypeError("use UTC (Z)")
    if dt.year < 1963 or dt.second or dt.microsecond:
        raise argparse.ArgumentTypeError("use a modern UTC date at whole-minute precision")
    return dt.replace(tzinfo=timezone.utc)


def horizons_rows(payload, target, observer, start, stop, step):
    if payload.get("error"):
        raise ValueError(payload["error"])
    version = payload.get("signature", {}).get("version")
    if version not in {"1.2", "1.3"}:
        raise ValueError(f"unrecognized Horizons API version {version!r}. Inspect raw JSON and API documentation.")
    raw = payload.get("result", "")
    if not re.search(r"Target body name:.*\(" + target + r"\)", raw):
        raise ValueError("response target does not match the request")
    position = re.search(r"Center geodetic\s*:\s*([-+\d.eE]+),\s*([-+\d.eE]+),\s*([-+\d.eE]+)", raw)
    if not re.search(r"Center body name:.*Moon \(301\)", raw) or not position:
        raise ValueError("response is missing the lunar surface observer")
    lon, lat, alt = map(float, position.groups())
    expected_lon, expected_lat, expected_alt = observer
    # Horizons prints rounded coordinates in the header and can normalize east longitude to [0, 360).
    lon_error = abs((lon-expected_lon+180) % 360-180)
    if max(lon_error, abs(lat-expected_lat), abs(alt-expected_alt)) > 0.00011:
        raise ValueError("response observer coordinates do not match the request")
    if not re.search(r"Date__\(UT\).*Azi_\(a-app\).*Elev_\(a-app\)", raw):
        raise ValueError("response is missing UT and apparent airless angle columns")
    before, marker, after = raw.partition("$$SOE")
    body, end, _ = after.partition("$$EOE")
    if not marker or not end:
        raise ValueError("response is missing ephemeris table markers")
    rows = []
    previous = None
    months = {m: i for i, m in enumerate("Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split(), 1)}
    for row in csv.reader(body.strip().splitlines()):
        if not row or not row[0].strip():
            continue
        stamp = re.fullmatch(r"(\d{4})-([A-Za-z]{3})-(\d{2}) (\d{2}):(\d{2})(?::00(?:\.0+)?)?", row[0].strip())
        if not stamp or len(row) < 5:
            raise ValueError(f"unexpected Horizons row: {row}")
        year, month, day, hour, minute = stamp.groups()
        dt = datetime(int(year), months[month], int(day), int(hour), int(minute), tzinfo=timezone.utc)
        if dt < start or dt > stop or (dt-start).total_seconds() % (60*step) or (previous and dt <= previous):
            raise ValueError(f"unexpected ephemeris timestamp: {dt.isoformat()}")
        az, el = (v.strip() for v in row[3:5])
        if az.lower() == "n.a." or el.lower() == "n.a." or not az or not el:
            az, el, state = "", "", "missing"
        else:
            a, e = float(az), float(el)
            if not (0 <= a <= 360 and -90 <= e <= 90):
                raise ValueError(f"invalid angles at {dt.isoformat()}")
            az, el, state = a % 360, e, "available"
        rows.append((dt.isoformat().replace("+00:00", "Z"), az, el, state))
        previous = dt
    expected = int((stop-start).total_seconds() // (step*60)) + 1
    if len(rows) != expected or not any(r[-1] == "available" for r in rows):
        raise ValueError(f"expected {expected} timestamps with usable angles. Received {len(rows)} rows.")
    return before, rows, version


def import_horizons_export(directory, payload, *, url, target, label, observer, start, stop, step, practice,
                           practice_reference=None, raw_source=None, synthetic_note=None):
    """The one importer: parse a Horizons reply, then write response.json, angles.csv and provenance.json.

    A row whose angles read ``n.a.`` is a valid gap. It keeps its UTC row in the CSV with an empty angle and
    ``angle_status=missing``, and the receipt records how many rows are missing and when. Bad observers, wrong
    targets, off-grid or duplicate timestamps and malformed numbers still raise ValueError.
    """
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    header, rows, version = horizons_rows(payload, target, observer, start, stop, step)
    raw = directory / "response.json"
    if raw_source is None:
        temp = directory / "response.json.part"
        temp.write_text(json.dumps(payload), encoding="utf-8")
        raw_source = temp
    if Path(raw_source) != raw:
        os.replace(raw_source, raw)
    csv_path = directory / "angles.csv"
    csv_tmp = csv_path.with_suffix(".csv.part")
    with csv_tmp.open("w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(("timestamp_utc", "azimuth_deg", "elevation_deg", "angle_status"))
        writer.writerows(rows)
    os.replace(csv_tmp, csv_path)
    missing = [row[0] for row in rows if row[-1] == "missing"]
    lon, lat, alt = observer
    receipt = {
        "source": HORIZONS_DOCS, "request_url": url, "api_version": version,
        "observer": [lon, lat, alt], "observer_units": ["deg E", "deg N", "km"],
        "target": label, "step_minutes": step, "raw_sha256": sha(raw),
        "csv_sha256": sha(csv_path), "row_count": len(rows), "header": header,
        "missing_row_count": len(missing), "missing_timestamps": missing,
        "practice": practice,
        "practice_point_reference": practice_reference,
    }
    if synthetic_note:
        receipt["synthetic"] = True
        receipt["synthetic_note"] = synthetic_note
    write_json(directory / "provenance.json", receipt)
    return len(rows)


def horizons_command(root, args):
    sites = args.site or []
    if args.practice:
        sites = [
            ("site04-p02-practice", -156.4386, -89.7812, 1.738902),
            ("malapert-practice", -2.93, -85.99, 0.0),
        ]
        start = args.start or parse_date("2025-01-01")
        stop = args.stop or parse_date("2025-01-03")
        print("Practice points. Malapert uses a 0 km reference height. Confirm exact coordinates and heights for the actual case.")
    else:
        if not sites or not args.start or not args.stop:
            raise ValueError("supply --site, --start and --stop, or use --practice")
        start, stop = args.start, args.stop
    if len({s[0] for s in sites}) != len(sites):
        raise ValueError("use unique site names")
    step = args.step_min
    if not (0 < step <= 1440 and 0 < (stop-start).total_seconds() <= step*60*10000):
        raise ValueError("choose positive step minutes and a time span of 1–10,000 intervals")
    if (stop-start).total_seconds() % (step*60):
        raise ValueError("choose a time span evenly divisible by --step-min")
    contact = args.contact.strip()
    if not re.fullmatch(r"(?:[^\s@]+@[^\s@]+\.[^\s@]+|https://[^\s]+)", contact) or not contact.isascii():
        raise ValueError("provide a contact email or HTTPS contact URL for the JPL User-Agent")
    agent = f"LunarLandingOfflinePack/1.0 ({contact})"
    failures = 0
    for name, lon, lat, alt in sites:
        for target, label in (("10", "sun"), ("399", "earth")):
            query = {
                "format": "json", "COMMAND": target, "OBJ_DATA": "NO", "MAKE_EPHEM": "YES",
                "EPHEM_TYPE": "OBSERVER", "CENTER": "coord@301", "COORD_TYPE": "GEODETIC",
                "SITE_COORD": f"{lon},{lat},{alt}", "START_TIME": start.strftime("%Y-%m-%d %H:%M"),
                "STOP_TIME": stop.strftime("%Y-%m-%d %H:%M"), "STEP_SIZE": f"{step} m",
                "QUANTITIES": "4", "CSV_FORMAT": "YES", "TIME_TYPE": "UT",
                "ELEV_CUT": "-90", "SKIP_DAYLT": "NO", "ANG_FORMAT": "DEG",
            }
            url = HORIZONS + "?" + urlencode({k: v if k == "format" else f"'{v}'" for k, v in query.items()})
            key = hashlib.sha256(url.encode()).hexdigest()[:12]
            directory = root / "horizons" / name / f"{label}-{key}"
            directory.mkdir(parents=True, exist_ok=True)
            raw = directory / "response.json"
            temp = directory / "response.json.part"
            try:
                if not raw.exists():
                    print(f"GET  Horizons {name} / {label}", flush=True)
                    if curl(url, temp, agent=agent):
                        raise RuntimeError("request failed. Rerun to retry. Completed requests are cached.")
                source = raw if raw.exists() else temp
                payload = json.loads(source.read_text(encoding="utf-8"))
                rows_written = import_horizons_export(
                    directory, payload, url=url, target=target, label=label, observer=(lon, lat, alt),
                    start=start, stop=stop, step=step, practice=args.practice,
                    practice_reference=PRACTICE_MALAPERT if name == "malapert-practice" else None,
                    raw_source=source,
                )
                print(f" OK  {rows_written:>5} rows  {directory / 'angles.csv'}")
            except (OSError, ValueError, RuntimeError, KeyError) as exc:
                print(f"FAIL {name} / {label}: {exc}\n     Inspect {raw if raw.exists() else temp}", file=sys.stderr)
                failures += 1
    return bool(failures)


def check_horizons(root):
    folders = sorted(p for p in (root / "horizons").glob("*/*") if p.is_dir())
    if not folders:
        print("FAIL no Horizons exports found", file=sys.stderr)
        return 1
    failures = 0
    for folder in folders:
        try:
            receipt = json.loads((folder / "provenance.json").read_text(encoding="utf-8"))
            if sha(folder / "response.json") != receipt["raw_sha256"]:
                raise ValueError("raw response SHA-256 mismatch")
            if sha(folder / "angles.csv") != receipt["csv_sha256"]:
                raise ValueError("angle CSV SHA-256 mismatch")
            print(f" OK  {receipt['row_count']:>5} rows  {folder / 'angles.csv'}")
        except (OSError, ValueError, KeyError) as exc:
            print(f"FAIL {folder}: {exc}", file=sys.stderr)
            failures += 1
    return int(bool(failures))


def wheels_command(root, args):
    # Tag the wheel cache with the actual Python and platform used to resolve it.
    import sysconfig
    tag = f"{sys.implementation.cache_tag}-{sysconfig.get_platform()}"
    dest = root / "offline" / "wheels" / tag
    dest.mkdir(parents=True, exist_ok=True)
    req = Path(args.requirements).resolve() if args.requirements else dest / "requirements-offline.txt"
    if args.requirements and args.jupyter:
        raise ValueError("add JupyterLab to your requirements file or use --jupyter with the default package set")
    if not args.requirements:
        packages = (*PYTHON_PACKAGES, "jupyterlab") if args.jupyter else PYTHON_PACKAGES
        req.write_text("\n".join(packages) + "\n", encoding="utf-8")
    subprocess.run([sys.executable, "-m", "pip", "download", "--only-binary=:all:",
                    "--dest", str(dest), "-r", str(req)], check=True)
    print(f"\nWheel cache: {dest}")
    print("On the matching demo laptop, use its Python and the same requirements file:")
    print(f'  python3 -m pip install --no-index --find-links "{dest}" -r "{req}"')
    if args.requirements:
        print("Bring the requirements file and any files it includes along with the wheel cache.")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples (run from the repository root):
  python3 lunar_offline_pack.py plan all
  python3 lunar_offline_pack.py fetch core terrain visibility spice visuals
  python3 lunar_offline_pack.py fetch candidates
  python3 lunar_offline_pack.py fetch upgrade
  python3 lunar_offline_pack.py check core terrain --open-dem
  python3 lunar_offline_pack.py horizons --practice --contact 'you@example.org'
  python3 lunar_offline_pack.py horizons --site 'test,-156.4386,-89.7812,1.738902' \
    --start 2025-01-01T00:00Z --stop 2025-01-03T00:00Z --step-min 15 --contact 'you@example.org'
  python3 lunar_offline_pack.py check-horizons
  python3 lunar_offline_pack.py wheels
  python3 lunar_offline_pack.py --root /media/usb/lunar-data fetch core terrain

Choose actual observer coordinates, height above the reference, and UTC dates
once your challenge case is set. For a +24 h comparison, keep ephemeris coverage
through the end of the shifted window. Product 69 is a long-term reference.
For an offline venue smoke test, install the cached wheels in a local venv,
disconnect Wi-Fi, and run check --open-dem and check-horizons.
""")
    parser.add_argument("--root", type=Path, default=Path("data"), help="destination directory (default: ./data)")
    cmd = parser.add_subparsers(dest="command", required=True)
    for name, help_text in (("plan", "show links and known download sizes"),
                            ("fetch", "download or resume selected public asset packs"),
                            ("check", "verify local asset files with no network")):
        c = cmd.add_parser(name, help=help_text)
        c.add_argument("packs", nargs="*", type=parse_pack, metavar="PACK", help="defaults to core")
        if name == "check":
            c.add_argument("--open-dem", action="store_true", help="also read one masked pixel per GeoTIFF with Rasterio")
    h = cmd.add_parser("horizons", help="save Sun and Earth observer tables, one request at a time")
    sites = h.add_mutually_exclusive_group(required=True)
    sites.add_argument("--site", action="append", type=parse_site, metavar="NAME,LON,LAT,ALT_KM")
    sites.add_argument("--practice", action="store_true", help="Site04 and Malapert example, 2025-01-01 to 03 by default")
    h.add_argument("--start", type=parse_date, help="UTC, e.g. 2025-01-01T00:00Z")
    h.add_argument("--stop", type=parse_date, help="UTC. Include shifted-date coverage if needed.")
    h.add_argument("--step-min", type=int, default=15)
    h.add_argument("--contact", required=True, help="email or HTTPS URL for JPL's User-Agent requirement")
    cmd.add_parser("check-horizons", help="verify checksums of saved observer exports with no network")
    wh = cmd.add_parser("wheels", help="download Python wheels for this interpreter and platform")
    wh.add_argument("--requirements", help="use the project's pinned requirements")
    wh.add_argument("--jupyter", action="store_true", help="include JupyterLab with the default packages")
    args = parser.parse_args()
    root = args.root.resolve()
    try:
        if args.command in {"fetch", "horizons"} and not shutil.which("curl"):
            raise RuntimeError("install curl on the connected computer")
        if args.command == "plan":
            plan(args.packs or ["core"])
            return 0
        if args.command in {"fetch", "check"}:
            return int(assets_command(root, args.packs or ["core"], args.command == "fetch",
                                      getattr(args, "open_dem", False)))
        if args.command == "horizons":
            return int(horizons_command(root, args))
        if args.command == "check-horizons":
            return check_horizons(root)
        return wheels_command(root, args)
    except KeyboardInterrupt:
        print("\nInterrupted. Rerun to resume static downloads.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
