#!/usr/bin/env python3
"""Create a deterministic git-apply integration kit, never a binary app package."""
import gzip
import hashlib
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]
BASE = "178ee738a246e0a7cfc1e7ea91e5915edce5b967"
NAME = "claude-wha-linux-compat-20261101"
EPOCH = 1793491200  # 2026-11-01 00:00 UTC


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def package():
    if git("rev-parse", "HEAD").decode().strip() != BASE:
        raise SystemExit("Review the integration baseline before packaging a different HEAD")
    names = git("ls-files", "--others", "--exclude-standard", "-z").decode().split("\0")
    patch = git("diff", "--no-color", BASE, "--", "README.md", "CHANGELOG.md")
    for name in sorted(filter(None, names)):
        p = Path(name)
        if name not in (".gitignore", "wha-linux.sh") and p.parts[0] not in ("buildkit", "tools", "tests", "docs"):
            raise ValueError("Unexpected untracked file: " + name)
        if p.suffix not in ("", ".py", ".sh", ".md", ".json", ".lock", ".txt") or (ROOT / p).is_symlink():
            raise ValueError("Not an authored text file: " + name)
        result = subprocess.run(["git", "diff", "--no-color", "--no-index", "--", "/dev/null", name],
                                cwd=ROOT, capture_output=True)
        if result.returncode != 1:
            raise ValueError("Cannot package " + name)
        patch += result.stdout
    files = {
        "integration.patch": patch,
        "README.md": (ROOT / "docs/INTEGRATION.md").read_bytes(),
        "TEST_RESULTS.json": (ROOT / "docs/TEST_RESULTS.json").read_bytes(),
        "wha-linux.sh": (ROOT / "wha-linux.sh").read_bytes(),
        "LICENSE": (ROOT / "LICENSE").read_bytes(),
        "apply.sh": b'''#!/bin/sh
set -eu
bundle=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
target=${1:-.}
(cd "$bundle" && sha256sum -c SHA256SUMS)
git -C "$target" rev-parse --show-toplevel >/dev/null
git -C "$target" apply --check "$bundle/integration.patch"
git -C "$target" apply "$bundle/integration.patch"
printf '%s\\n' 'Applied locally. Review git diff; nothing committed or pushed.'
''',
    }
    private = re.compile(rb"(?:/home/[\w.-]+/(?:codex|Downloads|\.config)/|192\.168\.|Bearer\s+[A-Za-z0-9._-]{16,}|(?:access|refresh)_token\s*[=:]\s*['\"]?[A-Za-z0-9._-]{16,}|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,})")
    for name, data in files.items():
        text = data.decode("utf-8")
        if private.search(data) or any(ord(c) < 32 and c not in "\n\r\t" for c in text):
            raise ValueError("Private or binary material: " + name)
    files["SHA256SUMS"] = "".join(hashlib.sha256(data).hexdigest() + "  " + name + "\n"
                                     for name, data in sorted(files.items())).encode()
    output = ROOT / "integration-dist"
    output.mkdir(exist_ok=True)
    archive = output / (NAME + ".tar.gz")
    with archive.open("wb") as stream:
        with gzip.GzipFile(filename="", mode="wb", fileobj=stream, mtime=0) as compressed:
            with tarfile.open(fileobj=compressed, mode="w") as tar:
                for name, data in sorted(files.items()):
                    info = tarfile.TarInfo(NAME + "/" + name)
                    info.size, info.mtime = len(data), EPOCH
                    info.mode = 0o755 if name.endswith(".sh") else 0o644
                    tar.addfile(info, io.BytesIO(data))
    checksum = hashlib.sha256(archive.read_bytes()).hexdigest()
    (output / (archive.name + ".sha256")).write_text(checksum + "  " + archive.name + "\n")
    print(json.dumps({"archive": str(archive), "bytes": archive.stat().st_size,
                      "sha256": checksum, "files": sorted(files), "privacy_audit": "PASS"}, indent=2))


if __name__ == "__main__":
    package()
