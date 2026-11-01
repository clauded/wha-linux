#!/usr/bin/env python3
"""Run authored regressions against a generated bundle, with isolated state."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
bundle = Path(sys.argv[1]).resolve()
if bundle.name == "run.sh":
    bundle = bundle.parent
if not (bundle / "build-metadata.json").is_file():
    raise SystemExit("usage: python3 tools/verify_build.py /path/to/WiiM-Home-Linux")
with tempfile.TemporaryDirectory(prefix="wha-regressions-") as name:
    target = Path(name)
    for folder in ("linux", "tests"):
        shutil.copytree(ROOT / "buildkit" / folder, target / folder,
                        ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(ROOT / "buildkit/verify.sh", target / "verify.sh")
    (target / "out").mkdir()
    (target / "out/WiiM-Home-Linux").symlink_to(bundle, target_is_directory=True)
    (target / "dist").symlink_to("out", target_is_directory=True)
    subprocess.run(["bash", str(target / "verify.sh")], check=True)
