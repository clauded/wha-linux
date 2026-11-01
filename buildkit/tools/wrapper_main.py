"""Entry point embedded inside wha-linux.sh (stdlib only until build)."""
import argparse
import fcntl
import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from pathlib import Path


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def unpack(files, destination):
    for filename, content in files.items():
        name = Path(filename)
        if name.is_absolute() or ".." in name.parts:
            raise SystemExit("Invalid build-kit entry: " + filename)
        path = destination / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        path.chmod(0o755 if path.suffix == ".sh" else 0o644)


def main(files, wrapper):
    parser = argparse.ArgumentParser(prog=wrapper.name, description="Build and launch native WiiM Home from your official macOS x86_64 DMG.")
    parser.add_argument("dmg", nargs="?", help="official installer downloaded from https://wiimhome.com/app")
    parser.add_argument("--build-only", action="store_true", help="build and verify resources without opening a window")
    parser.add_argument("--hide-to-tray", action="store_true", help="hide on X instead of quitting (this launch only)")
    parser.add_argument("--debug", action="store_true", help="enable detailed Python and Qt diagnostics (this launch only)")
    parser.add_argument("--allow-untested", "--force-untested-source", action="store_true", help="try an unlisted installer; structural/runtime/patch checks still apply")
    parser.add_argument("--unpack", metavar="DIRECTORY", help="unpack our tooling for inspection, without the installer or build")
    args = parser.parse_args(sys.argv[2:])
    if args.unpack:
        destination = Path(args.unpack).expanduser().resolve()
        if destination.exists() and any(destination.iterdir()):
            parser.error("--unpack requires a new or empty directory")
        unpack(files, destination)
        print(destination)
        return
    if not args.dmg:
        parser.error("pass the path to the official macOS x86_64 .dmg")
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        parser.error("this build requires Linux x86_64")
    source = Path(args.dmg).expanduser().resolve()
    if not source.is_file():
        parser.error("DMG not found: " + str(source))
    source_hash = digest(source)
    sources = json.loads(files["source-compatibility.json"])["tested_sources"]
    matched = next((s for s in sources if s["sha256"] == source_hash), None)
    if matched is None:
        expected = ", ".join(s["version"] for s in sources)
        if not args.allow_untested:
            parser.error("Installer version is newer/different than the tested source. Build may require patch review. Expected: %s; actual SHA-256: %s. Use --allow-untested for guarded testing." % (expected, source_hash))
        print("WARNING: untested installer %s; runtime and semantic patch checks remain mandatory." % source_hash, flush=True)
    else:
        print("Recognized %s (%s; %s)" % (matched["version"], source_hash, matched.get("validation", "historically tested")), flush=True)
    # Include both identities: a changed wrapper or installer never overwrites
    # a known-good installation. Virtualenv/interpreter paths stay fixed.
    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))).expanduser().resolve()
    root = data / "wha-linux" / digest(wrapper)[:20] / source_hash[:20]
    root.mkdir(parents=True, exist_ok=True)
    launcher = root / "out/WiiM-Home-Linux/run.sh"
    with (root / ".build.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if not (root / ".ready").is_file() or not launcher.is_file():
            rcc = os.environ.get("RCC") or next((p for p in ("/usr/lib/qt6/rcc", "/usr/lib/qt6/libexec/rcc", "/usr/lib64/qt6/libexec/rcc", "rcc") if shutil.which(p)), "rcc")
            archive_tool = shutil.which("7zz") or shutil.which("7z") or "7z"
            missing = [tool for tool in ("bash", "uv", archive_tool, rcc) if shutil.which(tool) is None]
            if missing:
                parser.error("Missing: %s. Arch/Manjaro: sudo pacman -S python uv 7zip qt6-base; Fedora: sudo dnf install python3 uv 7zip qt6-qtbase-devel" % ", ".join(missing))
            if not re.search(r"\b6\.", subprocess.check_output([rcc, "--version"], text=True, stderr=subprocess.STDOUT)):
                parser.error("Qt 6 rcc required; set RCC to the Qt 6 executable")
            unpack(files, root)
            env = dict(os.environ)
            env.pop("PYTHONPATH", None)
            env.pop("PYTHONHOME", None)
            env["PYTHONNOUSERSITE"] = "1"
            env["RCC"] = rcc
            env["WIIM_OFFICIAL_DMG"] = str(source)
            print("Building in " + str(root), flush=True)
            subprocess.run(["bash", str(root / "build.sh")], env=env, check=True)
            (root / ".ready").write_text(source_hash + "\n")
    if args.build_only:
        print("Ready: " + str(launcher))
        return
    print("Starting WiiM Home", flush=True)
    os.environ.pop("PYTHONPATH", None)
    os.environ.pop("PYTHONHOME", None)
    os.environ["PYTHONNOUSERSITE"] = "1"
    os.environ["WIIM_HIDE_TO_TRAY"] = "1" if args.hide_to_tray else "0"
    os.environ["WIIM_DEBUG"] = "1" if args.debug else "0"
    # Keep accounts/preferences across wrapper upgrades, separately from the
    # versioned generated application directory.
    os.environ.setdefault("XDG_DATA_HOME", str(data))
    os.environ.setdefault("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    os.environ.setdefault("XDG_CACHE_HOME", str(Path.home() / ".cache"))
    os.execv(str(launcher), [str(launcher)])


try:
    wrapper = Path(sys.argv[1]).resolve()
    contents = wrapper.read_text(encoding="utf-8").split("\n# === WHA FILES ===\n", 1)[1]
    contents = contents.rsplit("WHA_FILES\n", 1)[0]
    parts = re.split(r"(?m)^# === wha-file ([^\n]+) ===\n", contents)[1:]
    main(dict(zip(parts[::2], parts[1::2])), wrapper)
except subprocess.CalledProcessError as error:
    raise SystemExit("Build failed (exit %s); nothing was marked ready. Fix the error above, then rerun." % error.returncode)
except KeyboardInterrupt:
    raise SystemExit(130)
