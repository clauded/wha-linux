#!/usr/bin/env python3
"""Deterministic readable standalone launcher; only authored tooling is embedded."""
import hashlib
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / "buildkit"


def generate():
    names = {"build.sh", "source-compatibility.json"}
    names.update(p.name for p in KIT.glob("requirements-*.lock"))
    names.update(p.relative_to(KIT).as_posix() for p in (KIT / "linux").rglob("*.py") if "__pycache__" not in p.parts)
    names.update("tools/" + name + ".py" for name in (
        "extract_installer", "unpack_pyz", "inspect_source", "materialize_resources",
        "patch_qml", "rebuild_qt_resources", "verify_qrc"))
    names.update(p.relative_to(KIT).as_posix() for p in (KIT / "patches").iterdir() if p.suffix in (".txt", ".json"))
    loader = (KIT / "tools/wrapper_main.py").read_text()
    result = """#!/bin/sh
# Native WiiM Home, official macOS x86_64 DMG supplied by the user.
# Arch: sudo pacman -S python uv 7zip qt6-base
# Fedora: sudo dnf install python3 uv 7zip qt6-qtbase-devel
# Readable authored tooling only; no proprietary payload or encoded archive.
exec python3 - "$0" "$@" <<'WHA_LAUNCHER'
""" + loader + "WHA_LAUNCHER\n: <<'WHA_FILES'\n# === WHA FILES ===\n"
    private = re.compile(r"(?:/home/[\w.-]+/(?:codex|Downloads|\.config)/|192\.168\.|Bearer\s+[A-Za-z0-9._-]{16,}|(?:access|refresh)_token\s*[=:]\s*['\"]?[A-Za-z0-9._-]{16,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})")
    for name in sorted(names):
        content = (KIT / name).read_text()
        if not content.endswith("\n") or "\nWHA_FILES\n" in content or private.search(content):
            raise ValueError("Unsafe or private toolkit content: " + name)
        result += "# === wha-file " + name + " ===\n" + content
    result += "WHA_FILES\n"
    if private.search(loader):
        raise ValueError("Private launcher content")
    path = ROOT / "wha-linux.sh"
    path.write_text(result)
    path.chmod(0o755)
    print("%s: %d bytes, SHA-256 %s" % (path.name, len(result.encode()), hashlib.sha256(result.encode()).hexdigest()))


if __name__ == "__main__":
    generate()
