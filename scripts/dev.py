"""Small repository-owned developer checks and deterministic source packaging.

No publishing, tags, network access or extra runtime framework. The same
commands run locally and in the existing PR CI. Generated archives never
include private test, governance, site or local-cache content.
"""

from __future__ import annotations

import hashlib
import io
import json
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "robotix_multicharge"
MANIFEST = COMPONENT / "manifest.json"
ARTIFACTS = ROOT / "dist"
ALLOWED_SUFFIXES = {".py", ".json", ".js", ".css", ".html", ".svg", ".png", ".webp"}


def identity() -> dict:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    if manifest.get("domain") != "robotix_multicharge":
        raise ValueError("unexpected integration domain")
    if not isinstance(manifest.get("version"), str) or not manifest["version"]:
        raise ValueError("manifest must own a nonempty software version")
    if manifest.get("dependencies") != []:
        raise ValueError("MultiCharge must remain standalone")
    return manifest


def run(*command: str) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def test() -> None:
    run(sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v")


def check() -> None:
    identity()
    run(sys.executable, "-m", "compileall", "-q", "custom_components", "tests", "scripts")
    # Select correctness and syntax checks first; layout formatting is available
    # separately through "format" and can be applied in the existing PR.
    run(sys.executable, "-m", "ruff", "check", "--select", "F,E4,E7,E9",
        "custom_components", "tests", "scripts")
    run("node", "--check",
        "custom_components/robotix_multicharge/frontend/robotix-multicharge.js")
    test()


def archive_bytes() -> bytes:
    identity()
    files = sorted(
        p for p in COMPONENT.rglob("*")
        if p.is_file()
        and p.suffix in ALLOWED_SUFFIXES
        and "__pycache__" not in p.parts
        and not any(part.startswith(".") for part in p.relative_to(COMPONENT).parts)
    )
    if not files or MANIFEST not in files:
        raise ValueError("empty or incomplete integration package")
    output = io.BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for file in files:
            entry = ZipInfo(
                file.relative_to(ROOT).as_posix(),
                date_time=(1980, 1, 1, 0, 0, 0),
            )
            entry.compress_type = ZIP_DEFLATED
            entry.external_attr = 0o100644 << 16
            archive.writestr(entry, file.read_bytes(), compress_type=ZIP_DEFLATED,
                             compresslevel=9)
    data = output.getvalue()
    with ZipFile(io.BytesIO(data)) as archive:
        if archive.testzip() is not None:
            raise ValueError("corrupted source artifact")
        if len(archive.namelist()) != len(set(archive.namelist())):
            raise ValueError("duplicate packaged paths")
    return data


def package() -> None:
    manifest = identity()
    data = archive_bytes()
    if data != archive_bytes():
        raise ValueError("nondeterministic archive bytes")
    ARTIFACTS.mkdir(exist_ok=True)
    target = ARTIFACTS / f"robotix_multicharge-{manifest['version']}.zip"
    target.write_bytes(data)
    print(f"Package: {target.relative_to(ROOT)}")
    print(f"SHA256: {hashlib.sha256(data).hexdigest()}")
    print("Source-only development artifact; NOT a qualified HACS release")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in {
        "info", "check", "test", "format", "package",
    }:
        raise SystemExit("Usage: python scripts/dev.py info|check|test|format|package")
    command = sys.argv[1]
    if command == "info":
        item = identity()
        print(f"{item['name']} {item['version']} ({item['domain']})")
    elif command == "check":
        check()
    elif command == "test":
        test()
    elif command == "format":
        run(sys.executable, "-m", "ruff", "format",
            "custom_components", "tests", "scripts")
    else:
        package()


if __name__ == "__main__":
    main()
