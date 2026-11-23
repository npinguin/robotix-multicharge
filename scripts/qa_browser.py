#!/usr/bin/env python3
"""Real headless Chromium D0–D4 UI checks, with source-backed fake HA inputs.

This verifies browser DOM, responsive width, keyboard-native disclosure and
read-only roles. It does NOT claim an installed HA or physical Charger test.
"""
from __future__ import annotations

from html import unescape
import json
import re
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
PAGE = ROOT / "tests" / "fixtures" / "browser_smoke.html"
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


def run_case(chrome: str, size: int, count: int, role: str, view: str, dark: bool):
    query = urlencode({"count": count, "role": role, "view": view})
    url = PAGE.resolve().as_uri() + "?" + query
    label = f"{size}px_{count}chargers_{role}_{view}_{'dark' if dark else 'light'}"
    PROOF.mkdir(parents=True, exist_ok=True)
    screenshot = PROOF / (label + ".png")
    args = [
        chrome, "--headless=new", "--no-sandbox", "--disable-gpu",
        "--disable-dev-shm-usage", "--no-first-run", "--no-default-browser-check",
        "--hide-scrollbars", "--force-device-scale-factor=1",
        f"--window-size={size},900", "--virtual-time-budget=1900",
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
    if view in ("asset", "charger"):
        if row["cards"] != count:
            raise AssertionError(f"{label}: object count drift: {row}")
        if count and (not row["folds"] or not row["firstFoldClosed"]
                      or not row["keyboardSummary"] or not row["technicalReadable"]):
            raise AssertionError(f"{label}: inaccessible or missing owner fold: {row}")
    if view == "asset" and count:
        if row["goalEditable"] != (role == "admin"):
            raise AssertionError(f"{label}: novice goal or resident auth drift: {row}")
    if row["commandButtons"]:
        raise AssertionError(f"{label}: uncommissioned external Charger shows physical writes")
    if not screenshot.is_file() or screenshot.stat().st_size < 2000:
        raise AssertionError(f"{label}: browser screenshot missing")
    print(f"BROWSER PASS {label}: {row['cards']} objects, "
          f"{row['folds']} folds, {row['viewport']}px, {row['role']}")


def main():
    chrome = chrome_path()
    for case in CASES:
        run_case(chrome, *case)
    print(f"Real Chromium responsive source-UX PASS: {len(CASES)} cases "
          "(simulated HA input; installed target HA and real EVSE separately unqualified)")


if __name__ == "__main__":
    main()
