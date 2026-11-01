#!/usr/bin/env python3
"""Extract an official macOS WiiM Home DMG without executing it."""
import shutil, subprocess, sys
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: extract_installer.py <official-dmg> <destination>")
    source, output = map(lambda value: Path(value).resolve(), sys.argv[1:])
    tool = shutil.which("7zz") or shutil.which("7z")
    if not tool:
        raise SystemExit("Missing 7z/7zz. Arch/Manjaro: sudo pacman -S 7zip; Fedora: sudo dnf install 7zip")
    if output.exists():
        raise SystemExit("Extraction destination must be new: %s" % output)
    output.mkdir(parents=True)
    # The official DMG contains macOS-relative symlinks. p7zip declines some
    # as unsafe and returns status 2, even though Contents/Resources is fully
    # extracted. This build uses that payload directly, so validate it below.
    result = subprocess.run(
        [tool, "x", "-y", "-o" + str(output), str(source)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    apps = list(output.glob("**/WiiM Home.app/Contents/MacOS/WiiM Home"))
    if len(apps) != 1:
        raise SystemExit("Could not locate WiiM Home.app in official DMG (7z status %d)" % result.returncode)
    print(apps[0])

if __name__ == "__main__":
    main()
