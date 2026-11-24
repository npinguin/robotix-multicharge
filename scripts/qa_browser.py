#!/usr/bin/env python3
"""Real headless Chromium D0–D4 UI checks, with source-backed fake HA inputs.

This verifies browser DOM, responsive width, keyboard-native disclosure and
read-only roles. It does NOT claim an installed HA or physical Charger test.
"""
from __future__ import annotations

from html import unescape
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "tests" / "fixtures" / "browser_shell.html"
PROOF = ROOT / "dist" / "ux-browser-proof"

# Deliberately bounded real Chromium process count. All five count/role
# families, three actual viewport sizes and light/dark are represented.
CASES = [
    (390, 0, "admin", "overview", False),
    (390, 1, "admin", "asset", False),
    (390, 1, "resident", "asset", True),
    (390, 4, "admin", "charger", True),
    (390, 2, "resident", "charger", False),
    (1024, 4, "admin", "asset", False),
    (1024, 2, "resident", "asset", True),
    (1024, 10, "admin", "plan", True),
    (1600, 10, "resident", "overview", True),
    (1600, 10, "admin", "charger", False),
    (1600, 4, "admin", "overview", False),
    (1600, 1, "resident", "charger", True),
]


def chrome_path():
    for binary in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser"):
        if found := shutil.which(binary):
            return found
    raise RuntimeError("Real Chromium not installed; browser acceptance cannot PASS")


def run_case(chrome: str, base_url: str, size: int, count: int, role: str, view: str, dark: bool):
    query = urlencode({"width": size, "count": count, "role": role, "view": view})
    url = base_url + "/tests/fixtures/browser_shell.html?" + query
    label = f"{size}px_{count}chargers_{role}_{view}_{'dark' if dark else 'light'}"
    PROOF.mkdir(parents=True, exist_ok=True)
    screenshot = PROOF / (label + ".png")
    args = [
        chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
        "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
        "--hide-scrollbars", "--force-device-scale-factor=1",
        f"--window-size={max(500,size)},900", "--virtual-time-budget=3500",
        f"--screenshot={screenshot}", "--dump-dom",
    ]
    if dark:
        args.append("--force-dark-mode")
    args.append(url)
    proc = subprocess.run(args, capture_output=True, text=True, timeout=55)
    match = re.search(r'<pre id="smoke-result">([^<]+)</pre>', proc.stdout)
    if proc.returncode != 0 or not match:
        raise AssertionError(f"{label}: browser process failed ({proc.returncode}): "
                             + proc.stderr[-600:] + proc.stdout[-400:])
    row = json.loads(unescape(match.group(1)))
    if row.get("fatal"):
        raise AssertionError(f"{label}: {row['fatal']}")
    if not row.get("render"):
        raise AssertionError(f"{label}: bundled custom card did not render")
    if row["tabs"] != [
        "Overview", "Charging Plan", "Chargeable Assets", "Chargers", "Settings"
    ]:
        raise AssertionError(f"{label}: five-tab UX drift: {row['tabs']}")
    if row["documentWidth"] > row["viewport"] + 3:
        raise AssertionError(f"{label}: horizontal page overflow: {row}")
    if row["viewport"] != size:
        raise AssertionError(f"{label}: requested width not actually honored: {row}")
    if view == "goal":
        required = ("initial", "compact", "actionable", "allDays", "noImplicitWrite",
                    "saved", "reopened", "shared", "variants")
        if not all(row.get(key) is True for key in required):
            raise AssertionError(f"{label}: resident outcome/schedule journey failed: {row}")
        if not screenshot.is_file() or screenshot.stat().st_size < 2000:
            raise AssertionError(f"{label}: resident outcome screenshot missing")
        print(f"BROWSER PASS {label}: goal metrics, real-shaped timeline, compact schedule, one Save/readback")
        return
    if view == "edit":
        required = ("focused", "inputRetained", "backgroundSaved",
                    "dirtyRetained", "rejectedRetained", "explicitRepaint")
        if not all(row.get(key) is True for key in required):
            raise AssertionError(f"{label}: an edit was auto-closed or lost: {row}")
        if row.get("backendResponses", 0) < 2:
            raise AssertionError(f"{label}: 350ms background update not exercised: {row}")
        if not screenshot.is_file() or screenshot.stat().st_size < 2000:
            raise AssertionError(f"{label}: browser edit screenshot missing")
        print(f"BROWSER PASS {label}: active and dirty input survives HA + "
              "late source requests, rejected save, 350ms refresh")
        return
    if view == "yaml":
        required = ("textareaOpen", "saveAvailable", "draftRetained",
                    "savedConfirmed", "cancelled")
        if not all(row.get(key) is True for key in required):
            raise AssertionError(f"{label}: YAML review/save/regression failed: {row}")
        if row.get("backendResponses", 0) < 2:
            raise AssertionError(f"{label}: HA refresh did not occur: {row}")
        if not screenshot.is_file() or screenshot.stat().st_size < 2000:
            raise AssertionError(f"{label}: YAML screenshot missing")
        print(f"BROWSER PASS {label}: direct YAML Save/readback, "
              "350ms refresh and explicit Cancel")
        return
    if view in ("asset", "charger"):
        if row["cards"] != count:
            raise AssertionError(f"{label}: object count drift: {row}")
        if count and (not row["folds"] or not row["firstFoldClosed"]
                      or not row["keyboardSummary"] or not row["technicalReadable"]):
            raise AssertionError(f"{label}: inaccessible or missing owner fold: {row}")
    if view == "asset" and count:
        if row["goalEditable"] != (role == "admin"):
            raise AssertionError(f"{label}: novice goal or resident auth drift: {row}")
    if view == "overview":
        if not row["siteFirst"] or row["quickSelectors"] != 0 or row["assetAssignmentActions"] != (count if role == "admin" else 0):
            raise AssertionError(f"{label}: site-first asset assignment hierarchy lost: {row}")
    if view == "charger":
        if row["quickSelectors"] != count:
            raise AssertionError(f"{label}: top-level Charger vehicle quick action missing: {row}")
        if row["quickEditable"] != (count if role == "admin" else 0):
            raise AssertionError(f"{label}: read-only resident or admin native select drift: {row}")
    if view == "plan" and count:
        # Two Chargers have source-qualified plan data; the remaining
        # lanes must not manufacture charts or measurements.
        if row["apexHosts"] < 1 or row["apexLive"] != row["apexHosts"]:
            raise AssertionError(f"{label}: all source-qualified local ApexCharts must render: {row}")
        if row.get("apexErrors"):
            raise AssertionError(f"{label}: a real browser ApexCharts error occurred: {row}")
        if not all(row.get(key) for key in ("legendContained", "legendToggle", "priceAndForecast", "sameRange", "colorAndQuarter")):
            raise AssertionError(f"{label}: price/forecast legend layout or interaction lost: {row}")
    if row["commandButtons"]:
        raise AssertionError(f"{label}: uncommissioned external Charger shows physical writes")
    if not screenshot.is_file() or screenshot.stat().st_size < 2000:
        raise AssertionError(f"{label}: browser screenshot missing")
    print(f"BROWSER PASS {label}: {row['cards']} objects, "
          f"{row['folds']} folds, {row['viewport']}px, {row['role']}")


class QuietFiles(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        pass


def main():
    chrome = chrome_path()
    # Serve the exact bundled source over a real local web origin. This also
    # makes the iframe genuinely same-origin and avoids Chromium file://
    # opaque-origin restrictions while testing its actual 390px viewport.
    server = ThreadingHTTPServer(("127.0.0.1", 0),
        partial(QuietFiles, directory=str(ROOT)))
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        for case in CASES:
            run_case(chrome, base, *case)
        # Same real bundled JS/Shadow DOM as production, three viewports.
        # These flows prove slow users can type through sensor refreshes.
        for width in (390, 1024, 1600):
            run_case(chrome, base, width, 1, "admin", "edit", False)
        for width in (390, 1024, 1600):
            run_case(chrome, base, width, 4, "admin", "yaml", False)
        for width in (390, 1024, 1600):
            run_case(chrome, base, width, 2, "admin", "goal", False)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    print(f"Real Chromium responsive source-UX PASS: {len(CASES) + 9} cases "
          "(simulated HA input; installed target HA and real EVSE separately unqualified)")


if __name__ == "__main__":
    main()
