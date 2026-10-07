#!/bin/sh
# Native WiiM Home: sh wha-linux-0.2.10.4.sh /path/to/official-x86_64.dmg
# Prerequisites (Arch): sudo pacman -S python uv 7zip qt6-base
# Only our tooling below; the official application comes from your DMG.
exec python3 - "$0" "$@" <<'WHA_LAUNCHER'
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
        parser.error("Installer version is newer/different than the tested source. Build may require patch review. Expected: %s; actual SHA-256: %s" % (expected, source_hash))
    print("Verified %s (%s)" % (matched["version"], source_hash), flush=True)

    data = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local/share"))).expanduser().resolve()
    root = data / "wha-linux" / digest(wrapper)[:20] / source_hash[:20]
    root.mkdir(parents=True, exist_ok=True)
    launcher = root / "out/WiiM-Home-Linux/run.sh"

    # Skip recompilation if built
    if (root / ".ready").is_file() and launcher.is_file():
        print("Existing build found. Skipping compilation.", flush=True)
    else:
        with (root / ".build.lock").open("a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            if not (root / ".ready").is_file() or not launcher.is_file():
                rcc = os.environ.get("RCC") or next((p for p in ("/usr/lib/qt6/rcc", "/usr/lib64/qt6/libexec/rcc", "rcc") if shutil.which(p)), "rcc")
                missing = [tool for tool in ("bash", "uv", "7z", rcc) if shutil.which(tool) is None]
                if missing:
                    parser.error("Missing: %s. Arch/Manjaro: sudo pacman -S python uv 7zip qt6-base" % ", ".join(missing))
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
WHA_LAUNCHER
: <<'WHA_FILES'
# === WHA FILES ===
# === wha-file build.sh ===
#!/usr/bin/env bash
set -euo pipefail
root=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
source_dmg=${WIIM_OFFICIAL_DMG:?Run ./bootstrap.sh --dmg /path/to/official.dmg}
command -v uv >/dev/null || { echo "Missing uv: install it from https://docs.astral.sh/uv/" >&2; exit 1; }
export RCC="${RCC:-rcc}"
command -v "$RCC" >/dev/null || { echo "Missing rcc. On Arch/Manjaro: sudo pacman -S qt6-base" >&2; exit 1; }
work="$root/work"
out="$root/out/WiiM-Home-Linux"
rm -rf "$work" "$out" "$root/dist"
mkdir -p "$work" "$root/out"
python3 "$root/tools/extract_installer.py" "$source_dmg" "$work/extracted"
binary=$(find "$work/extracted" -path '*WiiM Home.app/Contents/MacOS/WiiM Home' -type f -print -quit)
resources=$(dirname "$(dirname "$binary")")/Resources
[[ -n $binary && -d $resources ]] || { echo "Invalid extracted official application" >&2; exit 1; }
export UV_CACHE_DIR="${UV_CACHE_DIR:-$root/.uv-cache}"
UV_PYTHON_INSTALL_DIR="$work/python" UV_PYTHON_BIN_DIR="$work/bin" uv python install 3.9.25
py39=$(find "$work/python" -type f -path '*/bin/python3.9' -print -quit)
[[ -n $py39 ]] || { echo "uv did not install Python 3.9" >&2; exit 1; }
uv run --python "$py39" --with pyinstaller python "$root/tools/unpack_pyz.py" "$binary" "$work/pyz"
uv venv --python "$py39" "$out/runtime/venv"
uv pip install --python "$out/runtime/venv/bin/python" -r "$root/requirements-linux.lock"
mkdir -p "$out/app" "$out/resources"
cp -a "$work/pyz/." "$out/app/"
cp -a "$resources/data" "$out/app/"
mkdir -p "$out/app/HOME"
cp -a "$resources/data" "$out/app/HOME/"
cp -a "$resources/Qml" "$out/app/"
cp -a "$resources/images" "$out/app/"
python3 "$root/tools/apply_edits.py" "$root/patches/edits.json" "tidal-home-loading.patch" "$out/app"
python3 "$root/tools/apply_edits.py" "$root/patches/edits.json" "tidal-collection-item-count.patch" "$out/app"
python3 "$root/tools/apply_edits.py" "$root/patches/edits.json" "tidal-collection-diagnostics.patch" "$out/app"
"$out/runtime/venv/bin/python" "$root/tools/rebuild_qt_resources.py" "$out/app"
PYTHONPATH="$out/runtime/venv/lib/python3.9/site-packages:$out/app" \
  "$out/runtime/venv/bin/python" "$root/tools/verify_qrc.py" "$out/app"
cp -a "$resources/Qml" "$out/resources/"
cp -a "$resources/images" "$out/resources/"
cp "$root/linux/bootstrap.py" "$root/linux/preset_fix.py" "$root/linux/sound_output_fix.py" "$root/linux/single_instance.py" "$root/linux/observer_lifecycle_fix.py" "$root/linux/cache_compat.py" "$root/linux/wiimradio_artwork_fallback.py" "$root/linux/app_icon.py" "$out/"
mkdir -p "$out/app/LPClientFramework/util"
cp "$root/linux/LPClientFramework/util/LPNativeCrashHandler.py" "$out/app/LPClientFramework/util/"
ln -s out "$root/dist"
cat > "$out/run.sh" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
base=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
export PYTHONPATH="$base/runtime/venv/lib/python3.9/site-packages:$base/app"
export WIIM_HOME_RESOURCES="$base/resources" WIIM_HOME_APP="$base/app"
export XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"
export XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-$HOME/.cache}"
export BEETSDIR="${BEETSDIR:-$XDG_CONFIG_HOME/beets}"

# Plasma 6 native integration flags
export QT_QPA_PLATFORMTHEME="${QT_QPA_PLATFORMTHEME:-kde}"
export QT_WAYLAND_DISABLE_WINDOWDECORATION=0

mkdir -p "$XDG_DATA_HOME" "$XDG_CONFIG_HOME" "$XDG_CACHE_HOME" "$BEETSDIR"
cd "$base/app"; exec "$base/runtime/venv/bin/python" "$base/bootstrap.py" "$@"
EOF
chmod +x "$out/run.sh"
echo "Built $out"
# === wha-file linux/LPClientFramework/util/LPNativeCrashHandler.py ===
"""Linux replacement for the small macOS/Windows crash-handler adapter.

The WiiM application itself already selects a no-op native handler on Linux;
this adapter supplies its writable crash directory using XDG state/data paths.
"""
import datetime
import faulthandler
import os
import traceback

def get_crash_dir():
    base = os.environ.get("XDG_STATE_HOME") or os.environ.get("XDG_DATA_HOME")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    path = os.path.join(base, "WiiMHome", "crashes")
    os.makedirs(path, exist_ok=True)
    return path

def install_native_crash_handler():
    return None

def generate_crash_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def _write_python_traceback_simple(dump_path=None):
    path = os.path.join(get_crash_dir(), "python_%s.log" % generate_crash_timestamp())
    with open(path, "w", encoding="utf-8") as stream:
        traceback.print_exc(file=stream)
        faulthandler.dump_traceback(file=stream)
    return path

# === wha-file linux/app_icon.py ===
"""Give the native Qt application a stable Plasma 6 identity and WiiM icon."""
import os
import shlex
import sys
from pathlib import Path


_APP_ID = "org.wiim.home"
_APP_NAME = "WiiM Home"

def icon_path(app_root=None):
    """Return the official multi-resolution WiiM icon shipped by the input."""
    root = Path(app_root or os.environ["WIIM_HOME_APP"])
    return root / "images" / "app.ico"


def desktop_entry_path(app_root=None):
    """Use KDE/XDG standard user application directory."""
    root = Path(app_root or os.environ["WIIM_HOME_APP"]).resolve()
    configured = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")).resolve()
    if configured == root.parent / "data" or root in configured.parents:
        configured = Path.home() / ".local" / "share"
    return configured / "applications" / (_APP_ID + ".desktop")


def desktop_entry_text(app_root=None):
    root = Path(app_root or os.environ["WIIM_HOME_APP"]).resolve()
    launcher = root.parent / "run.sh"
    if not launcher.is_file():
        launcher = root.parent.parent.parent / "run.sh"
    icon = root / "images" / "ico.png"
    return """[Desktop Entry]
Type=Application
Name=%s
GenericName=Audio Control Center
Comment=Control WiiM devices across your network
Exec=%s
Icon=%s
Terminal=false
Categories=AudioVideo;Audio;Player;Qt;
StartupWMClass=%s
X-KDE-Wayland-AppID=%s
StartupNotify=true
""" % (_APP_NAME, shlex.quote(str(launcher)), str(icon), _APP_ID, _APP_ID)


def ensure_desktop_entry(app_root=None):
    path = desktop_entry_path(app_root)
    content = desktop_entry_text(app_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text(encoding="utf-8") == content:
            return path
        path.write_text(content, encoding="utf-8")
        return path
    except (PermissionError, OSError) as err:
        sys.stderr.write("Warning: Could not write desktop entry: %s\n" % err)
        return path


def configure_application(application):
    """Set Plasma 6 Wayland/X11 app identity before windows map."""
    application.setApplicationName(_APP_NAME)
    if hasattr(application, "setApplicationDisplayName"):
        application.setApplicationDisplayName(_APP_NAME)
    if hasattr(application, "setDesktopFileName"):
        application.setDesktopFileName(_APP_ID)
    return ensure_desktop_entry()


def install_app_icon():
    """Install app metadata and icon before the main window becomes visible."""
    from PyQt6.QtCore import Qt
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication
    from HOME import LPApplication as application_module
    from HOME import WiiMHome as home_module

    application_class = application_module.LPApplication
    window_class = home_module.LPStreamServiceMainWindow
    if getattr(window_class, "_linux_app_icon_installed", False):
        return
    original_setup = window_class.setupUi
    original_application_init = application_class.__init__

    def application_init(self, *args, **kwargs):
        result = original_application_init(self, *args, **kwargs)
        configure_application(self)
        return result

    def setup_ui(self, *args, **kwargs):
        result = original_setup(self, *args, **kwargs)

        # Enforce standard Plasma system window frame and titlebar decorations
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowMinMaxButtonsHint | Qt.WindowType.WindowCloseButtonHint)
        self.setAttribute(Qt.WidgetAttribute.WA_DontCreateNativeAncestors, False)
        self.setWindowFilePath("")

        path = icon_path()
        icon = QIcon(str(path))
        if icon.isNull():
            sys.stderr.write("Warning: WiiM application icon is unavailable: %s\n" % path)
        else:
            application = QApplication.instance()
            if application is not None:
                application.setWindowIcon(icon)
            self.setWindowIcon(icon)
        return result

    application_class.__init__ = application_init
    window_class.setupUi = setup_ui
    window_class._linux_app_icon_installed = True

# === wha-file linux/bootstrap.py ===
"""Native launcher compatibility flags for PyInstaller-reconstructed code."""
import argparse
import logging
import os
import runpy
import sys
import threading
import time

# Parse command line arguments (--debug switch, default OFF)
parser = argparse.ArgumentParser(description="WiiM Home Linux Native Launcher")
parser.add_argument(
    "--debug",
    action="store_true",
    default=False,
    help="Enable verbose debug logging output",
)
args, remaining_argv = parser.parse_known_args()

# Forward remaining arguments back to sys.argv
sys.argv = [sys.argv[0]] + remaining_argv

# Forcibly override all logging levels application-wide
if not args.debug:
    logging.disable(logging.INFO)
else:
    logging.disable(logging.NOTSET)
    logging.basicConfig(level=logging.DEBUG)

app = os.environ["WIIM_HOME_APP"]
from single_instance import AlreadyRunning, ObserverPortUnavailable, acquire, install_signal_cleanup, reserve_observer_port
try:
    _instance_lock = acquire()
except AlreadyRunning as error:
    print("WiiM Home: %s" % error, file=sys.stderr)
    raise SystemExit(2)
install_signal_cleanup()
try:
    reserve_observer_port()
except ObserverPortUnavailable as error:
    print("WiiM Home: %s" % error, file=sys.stderr)
    raise SystemExit(3)

# LPGlobalUI uses this flag to choose the original compiled *_ui Python
# classes instead of trying to find unbundled Qt Designer .ui files.
sys.frozen = True
sys._MEIPASS = app

from sound_output_fix import install_sound_output_fix
from cache_compat import ensure_http_cache_compatibility
from preset_fix import install_preset_fix
from observer_lifecycle_fix import install_observer_lifecycle_fix
from wiimradio_artwork_fallback import install_wiimradio_artwork_fallback
from app_icon import install_app_icon

install_preset_fix()
install_sound_output_fix()
ensure_http_cache_compatibility(os.environ["XDG_CACHE_HOME"] + "/com.linkplay.wiimhome")

import LPGlobalUI
install_observer_lifecycle_fix()
install_wiimradio_artwork_fallback()
install_app_icon()

from PyQt6.QtCore import QCoreApplication
from PyQt6.QtWidgets import QApplication

def _kill():
    time.sleep(0.1)
    os.kill(os.getpid(), 9)

def _force_exit():
    try:
        from LPClientFramework import LPUPnPObserverManager
        if hasattr(LPUPnPObserverManager, "LPUPnPObserverManager"):
            manager = getattr(LPUPnPObserverManager.LPUPnPObserverManager, "instance", None)
            if manager and hasattr(manager, "stop"):
                manager.stop()
    except Exception:
        pass
    threading.Thread(target=_kill, daemon=True).start()

orig_quit = QCoreApplication.quit
QCoreApplication.quit = lambda *a, **k: (_force_exit(), orig_quit(*a, **k))

# Override WiiMHome's window close/hide logic directly
from HOME import WiiMHome

def install_window_exit_patch():
    window_class = WiiMHome.LPStreamServiceMainWindow

    orig_close_event = getattr(window_class, "closeEvent", None)
    orig_hide = getattr(window_class, "hide", None)

    def close_event(self, event):
        if orig_close_event:
            try:
                orig_close_event(self, event)
            except Exception:
                pass
        _force_exit()

    def hide(self):
        if orig_hide:
            orig_hide(self)
        _force_exit()

    window_class.closeEvent = close_event
    window_class.hide = hide

install_window_exit_patch()

# Run main application entrypoint
runpy.run_path(os.path.join(app, "main.pyc"), run_name="__main__")
# === wha-file linux/cache_compat.py ===
"""Version-gate disposable requests-cache databases without touching user state."""
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


_DATABASES = ("tidal_request_cache.sqlite", "request_cache.sqlite", "wiimradio_api_cache.sqlite")
_MARKER = "requests-cache-runtime.json"
_DATETIME_MODE = "naive-utc"


def _runtime_marker():
    import requests_cache

    return {"requests_cache": requests_cache.__version__, "datetime_mode": _DATETIME_MODE}


def _response_count(path):
    with sqlite3.connect(path) as database:
        table = database.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='responses'").fetchone()
        return database.execute("SELECT count(*) FROM responses").fetchone()[0] if table else 0


def _clear_database(path, backup_dir):
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (path.stem + ".pre-cache-migration-" + datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + path.suffix)
    shutil.copy2(path, backup)
    with sqlite3.connect(path) as database:
        database.execute("DELETE FROM responses")
        table = database.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='redirects'").fetchone()
        if table:
            database.execute("DELETE FROM redirects")
        database.commit()
    return backup


def ensure_http_cache_compatibility(cache_root):
    """Invalidate only HTTP response caches when their runtime marker changes."""
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    marker_path = cache_root / _MARKER
    expected = _runtime_marker()
    try:
        observed = json.loads(marker_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        observed = None

    invalidated = []
    if observed != expected:
        backup_dir = cache_root / "requests-cache-backups"
        for name in _DATABASES:
            path = cache_root / name
            if path.exists() and _response_count(path):
                invalidated.append(str(_clear_database(path, backup_dir)))
    marker_path.write_text(json.dumps(expected, sort_keys=True) + "\n", encoding="utf-8")
    return invalidated
# === wha-file linux/observer_lifecycle_fix.py ===
"""Reliable lifecycle for WiiM Home's fixed-port UPnP observer server."""
import errno
import threading


def _transport_summary(message):
    if not isinstance(message, dict):
        return {}
    keys = ("playState", "duration", "progress", "lastPlayIndex", "trackId")
    summary = {key: message[key] for key in keys if key in message}
    if message.get("playUri"):
        summary["hasTrackUri"] = True
    return summary


def install_observer_lifecycle_fix():
    from LPClientFramework import LPUPnPObserverManager as module

    manager_class = module.LPUPnPObserverManager
    if getattr(manager_class, "_linux_observer_lifecycle_fix_installed", False):
        return

    if hasattr(manager_class, "_maintainSubscriptions"):
        original_server = module.LPThreadHTTPServer

        class ReservedObserverServer(original_server):
            def __init__(self, address, handler, bind_and_activate=True):
                from single_instance import take_observer_reservation
                reservation = take_observer_reservation(address[1]) if bind_and_activate else None
                if reservation is None:
                    super().__init__(address, handler, bind_and_activate=bind_and_activate)
                    return
                try:
                    super().__init__(address, handler, bind_and_activate=False)
                    self.socket.close()
                    self.socket = reservation
                    self.server_address = reservation.getsockname()
                    self.server_activate()
                except BaseException:
                    reservation.close()
                    raise
                module.logger.info("[UPnP observer] adopted startup reservation on 0.0.0.0:%d", address[1])

        module.LPThreadHTTPServer = ReservedObserverServer
        manager_class._linux_observer_lifecycle_fix_installed = True
        return

    original_stop = manager_class.stop

    def start(self):
        existing = getattr(self, "httpServer", None)
        existing_thread = getattr(self, "serverThread", None)
        if existing is not None or (existing_thread is not None and existing_thread.is_alive()):
            module.logger.debug("[UPnP observer] start ignored; server is already active")
            return True

        handler = module.partial(module.LPSimpleUPnPObserverHandler, self.messageDistributeMethod)
        try:
            from single_instance import take_observer_reservation
            reservation = take_observer_reservation(self.port)
            if reservation is None:
                server = module.LPThreadHTTPServer(("", self.port), handler)
            else:
                server = module.LPThreadHTTPServer(("", self.port), handler, bind_and_activate=False)
                unbound_socket = server.socket
                server.socket = reservation
                unbound_socket.close()
                server.server_address = reservation.getsockname()
                server.server_activate()
                module.logger.info("[UPnP observer] adopted startup reservation on 0.0.0.0:%d", self.port)
        except OSError as error:
            self.serverSwitch = False
            self.observerBindError = error
            if error.errno == errno.EADDRINUSE:
                module.logger.error(
                    "[UPnP observer] fixed listener 0.0.0.0:%d is occupied; "
                    "another WiiM Home instance or local service owns it", self.port,
                )
                return False
            raise

        self.serverSwitch = True
        self.observerBindError = None
        self.httpServer = server
        if not getattr(self, "_linux_transport_callback_wrapped", False):
            original_callback = self.notifyComeMethod

            def transport_callback(uuid, message):
                summary = _transport_summary(message)
                if summary:
                    module.logger.info(
                        "[UPnP transport] parsed callback device=%s fields=%s", uuid, summary,
                    )
                return original_callback(uuid, message)

            self.notifyComeMethod = transport_callback
            self._linux_transport_callback_wrapped = True

        def serve():
            module.logger.info("Start UPnP observer service on 0.0.0.0:%d", self.port)
            try:
                server.serve_forever()
            finally:
                server.server_close()

        self.serverThread = threading.Thread(target=serve, name="UPnPObserverServerThread", daemon=True)
        self.serverThread.start()

        def timeout_loop():
            while self.serverSwitch:
                for _ in range(60):
                    if not self.serverSwitch:
                        return
                    threading.Event().wait(1)
                with self.observerDictLock:
                    expired = [
                        value for value in self.observerDict.values()
                        if (module.datetime.datetime.now() - value["timestamp"]).total_seconds()
                        > value["timeout"] / 2
                    ]
                for value in expired:
                    def resubscribe(entry=value):
                        with self.observerDictLock:
                            self.observerDict.pop(entry["sid"], None)
                        result = self.subscribe(entry["ip"], entry["port"], entry["service"], entry["uuid"])
                        if result:
                            with self.observerDictLock:
                                self.observerDict.update(result)
                    threading.Thread(target=resubscribe, name="UPnPObserverResubscribe", daemon=True).start()

        self.timeoutThread = threading.Thread(target=timeout_loop, name="UPnPObserverTimeoutThread", daemon=True)
        self.timeoutThread.start()
        return True

    def stop(self):
        server_thread = getattr(self, "serverThread", None)
        original_stop(self)
        if server_thread is not None and server_thread is not threading.current_thread():
            server_thread.join(timeout=2)
        self.serverThread = None

    manager_class.start = start
    manager_class.stop = stop

    manager_class._linux_observer_lifecycle_fix_installed = True
# === wha-file linux/preset_fix.py ===
"""Narrow protocol validation for WiiM's asynchronous preset mapping reply."""
import re
from bs4 import BeautifulSoup


class PresetProtocolError(ValueError):
    pass


def _redacted_xml_for_log(xml_text):
    redacted = re.sub(
        r"(?is)<(access_?token|refresh_?token|token|password|authorization)[^>]*>.*?</\1\s*>",
        r"<\1>[redacted]</\1>",
        xml_text,
    )
    redacted = re.sub(r"(?i)(access_?token|refresh_?token|token|password)=([^&\s<'\"]+)", r"\1=[redacted]", redacted)
    return redacted[:2048]


def parse_key_mapping(xml_text, preset_count):
    if not isinstance(xml_text, str):
        raise PresetProtocolError("GetKeyMapping returned a non-text QueueContext")
    key_list = BeautifulSoup(xml_text, "xml").find("KeyList")
    if key_list is None:
        raise PresetProtocolError("GetKeyMapping QueueContext has no KeyList")
    slots = []
    for index in range(1, max(0, int(preset_count)) + 1):
        key = key_list.find("Key%d" % index)
        slot = {"index": index, "name": "", "source": "", "picUrl": ""}
        if key is not None:
            name = key.find("Name")
            if name is not None:
                slot["name"] = name.text
                source = key.find("Source")
                picture = key.find("PicUrl")
                slot["source"] = source.text if source is not None else ""
                slot["picUrl"] = picture.text if picture is not None else ""
        slots.append(slot)
    return slots


def install_preset_fix():
    from HOME import LPPresetViewController as preset_module
    import LPGlobalUI

    controller_class = preset_module.LPPresetViewController
    state = preset_module.LPPresetViewControllerState
    logger = preset_module.logger

    def fetch_preset_list(self):
        def finish(response):
            device = LPGlobalUI.currentDevice
            xml_text = response.get("xml") if isinstance(response, dict) else None
            response_error = response.get("error") if isinstance(response, dict) else "invalid response"
            logger.info(
                "[Preset] GetKeyMapping response status=%s xml_chars=%s",
                response.get("status_code") if isinstance(response, dict) else None,
                len(xml_text) if isinstance(xml_text, str) else None,
            )
            if response_error is not None:
                self.status = state.error
                self.updateUISignal.emit()
                return
            try:
                logger.debug("[Preset] GetKeyMapping XML before parse (redacted): %s", _redacted_xml_for_log(xml_text))
                slots = parse_key_mapping(xml_text, getattr(device, "presetNum", 0))
            except PresetProtocolError as error:
                logger.warning("[Preset] invalid GetKeyMapping payload: %s", error)
                self.presetList = []
                self.status = state.error
                self.updateUISignal.emit()
                return
            self.presetList = []
            for slot in slots:
                item = preset_module.LPPresetItem()
                item.index = slot["index"]
                item.name = slot["name"]
                item.source = slot["source"]
                item.picUrl = slot["picUrl"]
                self.presetList.append(item)
            self.status = state.ready
            self.updateUISignal.emit()

        device = LPGlobalUI.currentDevice
        if device is None or getattr(device, "presetNum", 0) == 0:
            self.status = state.notSupport
            self.updateUISignal.emit()
            return
        device.asyncUpnpPost("GetKeyMapping", {}, finish)

    controller_class._fetchPresetList = fetch_preset_list
# === wha-file linux/single_instance.py ===
"""Linux process guard for WiiM Home's fixed local listener set."""
import errno
import os
import socket


_observer_reservation = None


class AlreadyRunning(RuntimeError):
    pass


class ObserverPortUnavailable(RuntimeError):
    pass


def acquire():
    import fcntl

    directory = os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("XDG_CACHE_HOME")
    if not directory:
        directory = os.path.join(os.environ.get("WIIM_HOME_APP", "."), "cache")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "wiim-home-linux.lock")
    handle = open(path, "a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        if error.errno not in (errno.EACCES, errno.EAGAIN):
            raise
        handle.seek(0)
        owner = handle.read().strip() or "unknown"
        handle.close()
        raise AlreadyRunning("WiiM Home is already running (lock owner PID %s)" % owner)
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def install_signal_cleanup():
    """Let SIGTERM/SIGINT travel through Qt's normal close lifecycle."""
    import signal
    import threading
    import time

    def _hard_kill():
        time.sleep(0.1)
        os.kill(os.getpid(), 9)

    def request_quit(signum, _frame):
        threading.Thread(target=_hard_kill, daemon=True).start()

    signal.signal(signal.SIGTERM, request_quit)
    signal.signal(signal.SIGINT, request_quit)


def reserve_observer_port(port=22334):
    global _observer_reservation
    if _observer_reservation is not None:
        return _observer_reservation
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("0.0.0.0", port))
        listener.listen(5)
    except OSError as error:
        listener.close()
        if error.errno == errno.EADDRINUSE:
            raise ObserverPortUnavailable(
                "UPnP observer port %d is already in use; quit the process owning it before starting WiiM Home" % port
            )
        raise
    _observer_reservation = listener
    return listener


def take_observer_reservation(port):
    global _observer_reservation
    listener = _observer_reservation
    if listener is None or listener.getsockname()[1] != port:
        return None
    _observer_reservation = None
    return listener
# === wha-file linux/sound_output_fix.py ===
"""Normalize WiiM USB audio-output records for the original sound-settings UI."""
import logging


_UAC_MODE = "AUDIO_OUTPUT_UAC_CARD_MODE"


def _entry_shape(entry):
    if not isinstance(entry, dict):
        return {"type": type(entry).__name__}
    sound_card = entry.get("soundCard")
    return {
        "mode": entry.get("mode"),
        "keys": sorted(entry.keys()),
        "soundCard_type": type(sound_card).__name__,
        "soundCard_keys": sorted(sound_card.keys()) if isinstance(sound_card, dict) else [],
        "has_devName": "devName" in entry,
    }


def normalize_audio_outputs(output_array, current_output, current_output_device_name, logger=None):
    if not isinstance(output_array, list):
        return output_array

    if logger is not None:
        logger.debug(
            "[SoundOutput] pre-UI normalize output_count=%s current_output=%r entries=%s",
            len(output_array), current_output, [_entry_shape(item) for item in output_array],
        )

    normalized = []
    for item in output_array:
        if not isinstance(item, dict) or item.get("mode") != _UAC_MODE:
            normalized.append(item)
            continue

        device_name = item.get("devName")
        sound_card = item.get("soundCard")
        if not device_name and isinstance(sound_card, dict):
            device_name = sound_card.get("devName")
            if device_name:
                item["devName"] = device_name
                if logger is not None:
                    logger.debug("[SoundOutput] promoted soundCard.devName for UAC output")

        is_current = item.get("type") == current_output
        if not device_name and is_current and current_output_device_name:
            item["devName"] = current_output_device_name
            device_name = current_output_device_name
            if logger is not None:
                logger.debug("[SoundOutput] used active-output identity for UAC output")

        if not device_name and is_current:
            if logger is not None:
                logger.warning("[SoundOutput] withholding incomplete active UAC output: %s", _entry_shape(item))
            continue
        normalized.append(item)
    return normalized


def install_sound_output_fix():
    from HOME.DeviceSetting import LPDeviceSettingSoundViewController as sound_module

    controller_class = sound_module.LPDeviceSettingSoundViewController
    if getattr(controller_class, "_linux_sound_output_fix_installed", False):
        return
    original = controller_class._updateAudioOutputUI
    logger = getattr(sound_module, "logger", logging.getLogger(__name__))

    def update_audio_output_ui(self):
        self.outputArray = normalize_audio_outputs(
            getattr(self, "outputArray", None),
            getattr(self, "currentOutput", None),
            getattr(self, "currentOutputDeviceName", None),
            logger,
        )
        return original(self)

    controller_class._updateAudioOutputUI = update_audio_output_ui
    controller_class._linux_sound_output_fix_installed = True
# === wha-file linux/wiimradio_artwork_fallback.py ===
"""Bridge WiiM Radio's locally cached station art into device media state."""
import logging


_SOURCE = "WiiMRadio"
_STOPPED = "STOPPED"


def _text(value):
    return str(value or "").strip()


def _is_valid_pixmap(pixmap):
    return pixmap is not None and not pixmap.isNull()


def _local_pixmap(source):
    from PyQt6.QtCore import QUrl
    from PyQt6.QtGui import QPixmap

    source = _text(source)
    if source.startswith("file:"):
        source = QUrl(source).toLocalFile()
    elif source.startswith("qrc:/"):
        source = ":" + source[3:]
    if not source:
        return None
    pixmap = QPixmap(source)
    return pixmap if _is_valid_pixmap(pixmap) else None


class WiiMRadioArtworkFallback:

    def __init__(self, pixmap_loader=_local_pixmap, logger=None):
        self._records = {}
        self._pixmap_loader = pixmap_loader
        self._logger = logger or logging.getLogger(__name__)

    @staticmethod
    def _key(device):
        return _text(getattr(device, "uuid", "")) or "object:%s" % id(device)

    def remember_station(self, device, station):
        if device is None or not isinstance(station, dict):
            return
        station_id = _text(station.get("stationId") or station.get("StationID"))
        stream_url = _text(station.get("streamUrl") or station.get("StreamUrl"))
        thumbnail = _text(station.get("faviconThumbPath") or station.get("FaviconThumbPath"))
        if not thumbnail or (not station_id and not stream_url):
            return
        self._records[self._key(device)] = {
            "station_id": station_id,
            "stream_url": stream_url,
            "thumbnail": thumbnail,
        }

    def clear(self, device):
        if device is not None:
            self._records.pop(self._key(device), None)

    @staticmethod
    def _same_station(media, record):
        track_id = _text(getattr(media, "trackId", ""))
        play_uri = _text(getattr(media, "playUri", ""))
        if track_id and record["station_id"] and track_id != record["station_id"]:
            return False
        if play_uri and record["stream_url"] and play_uri != record["stream_url"]:
            return False
        return True

    def reconcile(self, device):
        media = getattr(device, "mediaInfo", None)
        if media is None or _text(getattr(media, "trackSource", "")) != _SOURCE:
            self.clear(device)
            return False
        if _text(getattr(media, "playState", "")) == _STOPPED:
            self.clear(device)
            return False
        record = self._records.get(self._key(device))
        if record is None:
            return False
        if not self._same_station(media, record):
            self.clear(device)
            return False
        if _is_valid_pixmap(getattr(media, "artworkImage", None)):
            return False
        pixmap = self._pixmap_loader(record["thumbnail"])
        if not _is_valid_pixmap(pixmap):
            return False
        media.artworkImage = pixmap
        self._logger.debug("[WiiMRadio][artwork] applied selected-station thumbnail fallback")
        return True


def install_wiimradio_artwork_fallback():
    from HOME.StreamService.WiiMRadio import LPWiiMRadioPlayController as play_module
    from LPClientFramework import LPDevice as device_module
    from LPClientFramework import LPUtility as utility_module

    device_class = device_module.LPDevice
    if getattr(device_class, "_linux_wiimradio_artwork_fallback_installed", False):
        return
    fallback = WiiMRadioArtworkFallback(logger=getattr(play_module, "logger", None))
    original_play = play_module.LPWiiMRadioPlayController.playStation
    original_set = device_class.setMediaInfo
    original_update = device_class.updateMediaInfo

    def notify_if_applied(device):
        if fallback.reconcile(device):
            utility_module.triggerDeviceInfoUpdate(device, "media", {"artworkFallback": True})

    def play_station(self, station_item):
        device = getattr(play_module.LPGlobalUI, "currentDevice", None)
        fallback.remember_station(device, station_item)
        return original_play(self, station_item)

    def set_media_info(self, media_info):
        result = original_set(self, media_info)
        notify_if_applied(self)
        return result

    def update_media_info(self, media_info):
        result = original_update(self, media_info)
        notify_if_applied(self)
        return result

    play_module.LPWiiMRadioPlayController.playStation = play_station
    device_class.setMediaInfo = set_media_info
    device_class.updateMediaInfo = update_media_info
    device_class._linux_wiimradio_artwork_fallback_installed = True
# === wha-file patches/edits.json ===
{
  "tidal-collection-diagnostics.patch": {
    "Qml/Tidal/sections/TidalHomeTrackGridSection.qml": [
      {
        "length": 6,
        "sha256": "f1abeb4cf886100447337f6c0c92763709c13e5dcd391c5942d64d06d2abbd30",
        "edits": [
          {
            "line": 3,
            "remove": 0,
            "insert_file": "insert-03.txt"
          }
        ]
      },
      {
        "length": 6,
        "sha256": "ea5ea8243dd0a01fdb97727b9b54131854fd53ea940750d4c31912ae59e53cfa",
        "edits": [
          {
            "line": 3,
            "remove": 0,
            "insert_file": "insert-04.txt"
          }
        ]
      }
    ],
    "Qml/Tidal/sections/TidalHomeRailSection.qml": [
      {
        "length": 6,
        "sha256": "c495b74ca60a9fb8e977397ea8bfa7936f7639f6004ef9ab340d5ec2b97aa99c",
        "edits": [
          {
            "line": 3,
            "remove": 0,
            "insert_file": "insert-05.txt"
          }
        ]
      }
    ],
    "Qml/Tidal/pages/TidalCollection.qml": [
      {
        "length": 6,
        "sha256": "a38c2b006564c350ee287db959854afe6af1e264adfb5368022125197e9e5203",
        "edits": [
          {
            "line": 3,
            "remove": 0,
            "insert_file": "insert-06.txt"
          }
        ]
      }
    ]
  },
  "tidal-collection-item-count.patch": {
    "Qml/Tidal/pages/TidalCollection.qml": [
      {
        "length": 6,
        "sha256": "465943fb891d95419196b3a881feeb72ff6a80209d9bdd12408a19ff9c941664",
        "edits": [
          {
            "line": 3,
            "remove": 0,
            "insert_file": "insert-07.txt"
          }
        ]
      },
      {
        "length": 10,
        "sha256": "bebb4c0b810dac7e1925bf8a9c50ff0519375dde3413a7a1c91d06cd87738ac5",
        "edits": [
          {
            "line": 3,
            "remove": 1,
            "insert_file": "insert-08.txt"
          },
          {
            "line": 6,
            "remove": 1,
            "insert_file": "insert-09.txt"
          }
        ]
      }
    ],
    "Qml/Tidal/sections/TidalHomeTrackGridSection.qml": [
      {
        "length": 7,
        "sha256": "a9543ed66f4de2dc6dac2c64034e9af011dd60ee16eae698911636ca8026e9e9",
        "edits": [
          {
            "line": 3,
            "remove": 1,
            "insert_file": "insert-10.txt"
          }
        ]
      },
      {
        "length": 8,
        "sha256": "55793b8d73ce060f05842592150be8def83e4acc61dcf81a99677110c4bf0d1e",
        "edits": [
          {
            "line": 3,
            "remove": 2,
            "insert_file": "insert-11.txt"
          }
        ]
      }
    ]
  },
  "tidal-home-loading.patch": {
    "Qml/Tidal/pages/TidalHome.qml": [
      {
        "length": 1,
        "sha256": "8373f58acf8c6270d6bd28565515de4230a3060a63c93d5bf9a19153300aee7f",
        "edits": [
          {
            "line": 0,
            "remove": 1,
            "insert_file": "insert-12.txt"
          }
        ]
      }
    ]
  }
}
# === wha-file patches/insert-03.txt ===
    readonly property int debugDelegateCount: trackRepeater.count
# === wha-file patches/insert-04.txt ===
            id: trackRepeater
# === wha-file patches/insert-05.txt ===
    readonly property int debugDelegateCount: listView.count
# === wha-file patches/insert-06.txt ===
            function logCollectionSection(label, section) {
                if (!section) {
                    return
                }
                var model = section.itemsModel
                var rows = model && model.rowCount !== undefined ? Number(model.rowCount()) : -1
                var effectiveCount = section.itemCount !== undefined ? Number(section.itemCount) : rows
                var delegates = section.debugDelegateCount !== undefined ? Number(section.debugDelegateCount) : -1
                root.debugLog("[TidalCollection] section=" + label
                              + " model=" + String(model)
                              + " rowCount=" + rows
                              + " qmlCount=not-bound"
                              + " effectiveItemCount=" + effectiveCount
                              + " visible=" + Boolean(section.visible)
                              + " height=" + Number(section.height)
                              + " delegates=" + delegates)
            }

            function logCollectionSectionsAfterUpdate() {
                if (!collectionContentRoot.sectionsReady) {
                    return
                }
                logCollectionSection("playlists", userPlaylistsSection)
                logCollectionSection("artists", favoriteArtistsSection)
                logCollectionSection("albums", favoriteAlbumsSection)
                logCollectionSection("tracks", favoriteTracksSection)
            }

            Connections {
                target: root.tidalCollectionState
                ignoreUnknownSignals: true

                function onCollectionDataChanged() {
                    Qt.callLater(collectionContentRoot.logCollectionSectionsAfterUpdate)
                }
            }

# === wha-file patches/insert-07.txt ===
    readonly property int collectionRevision: root.tidalCollectionState
                                                  ? Number(root.tidalCollectionState.revision || 0)
                                                  : 0
# === wha-file patches/insert-08.txt ===
        var revisionMarker = root.collectionRevision
        if (!modelObject) {
# === wha-file patches/insert-09.txt ===
        if (modelObject.rowCount !== undefined) {
            return Number(modelObject.rowCount()) > 0
        }
        return false
# === wha-file patches/insert-10.txt ===
# === wha-file patches/insert-11.txt ===
        if (root.itemsModel.rowCount !== undefined) {
            return Number(root.itemsModel.rowCount())
# === wha-file patches/insert-12.txt ===
                    sourceComponent: (!root.tidalHomeState || root.tidalHomeState.isInitialLoading) ? homeSkeletonComponent : homeContentComponent
# === wha-file requirements-linux.lock ===
annotated-doc==0.0.5
attrs==26.1.0
backports.tarfile==1.2.0
beautifulsoup4==4.15.0
beets==2.5.1
cattrs==25.3.0
certifi==2026.7.22
charset-normalizer==3.5.1
cheroot==11.1.2
CherryPy==18.10.0
click==8.1.8
confuse==2.1.0
exceptiongroup==1.3.1
filetype==1.2.0
idna==3.20
ifaddr==0.2.0
jaraco.collections==5.2.1
jaraco.context==6.1.1
jaraco.functools==4.4.0
jaraco.text==4.2.0
jellyfish==1.2.1
lap==0.5.13
lxml==6.1.3
markdown-it-py==3.0.0
mdurl==0.1.2
mediafile==0.13.0
more-itertools==10.8.0
musicbrainzngs==0.7.1
mutagen==1.47.0
numpy==2.0.2
pillow==11.3.0
platformdirs==4.4.0
portend==3.2.1
psutil==7.2.2
pycryptodome==3.23.0
Pygments==2.21.0
PyQt6==6.10.2
PyQt6-Qt6==6.10.2
PyQt6_sip==13.10.2
python-dateutil==2.9.0.post0
PyYAML==6.0.3
requests==2.32.5
requests-cache==1.0.1
requests-futures==1.0.2
rich==15.0.0
setuptools==82.0.1
shellingham==1.5.4
six==1.17.0
soupsieve==2.8.4
tempora==5.8.1
typer==0.23.2
typer-slim==0.23.2
typing_extensions==4.16.0
Unidecode==1.4.0
url-normalize==2.2.1
urllib3==2.6.3
watchdog==3.0.0
zc.lockfile==4.0
zeroconf==0.148.0
# === wha-file source-compatibility.json ===
{
  "tested_sources": [
    {
      "platform": "macOS x86_64 DMG",
      "version": "WiiM Home 0.2.10.4",
      "bundle_build": "20260920094034",
      "sha256": "5feefadf65905219bd9cdca09b967719ed8cdf38563aa5f67a065b3f2924d39f",
      "size_bytes": 78665242,
      "python": "CPython 3.9",
      "qt": "Qt 6 / PyQt6"
    }
  ]
}
# === wha-file tools/apply_edits.py ===
"""Apply source edits with deleted text represented only by SHA-256 hashes.

No original QML is embedded. The tested installer is verified separately;
each edit additionally checks the exact bytes it is about to replace.
"""
import hashlib
import json
import sys
from pathlib import Path


def apply_edits(manifest, patch_name, root):
    for filename, hunks in manifest[patch_name].items():
        path = root / filename
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        changes = []
        for hunk in hunks:
            length = hunk["length"]
            matches = [i for i in range(len(lines) - length + 1)
                       if hashlib.sha256("".join(lines[i:i + length]).encode()).hexdigest() == hunk["sha256"]]
            if len(matches) != 1:
                raise SystemExit("Patch review required: %s / %s: expected one context hash match, got %d" % (patch_name, filename, len(matches)))
            changes.extend((matches[0] + edit["line"], edit) for edit in hunk["edits"])
        for start, edit in sorted(changes, key=lambda item: item[0], reverse=True):
            count = edit["remove"]
            insertion = edit.get("insert")
            if insertion is None:
                insertion = (Path(sys.argv[1]).parent / edit["insert_file"]).read_text(encoding="utf-8")
            lines[start:start + count] = insertion.splitlines(keepends=True)
        path.write_text("".join(lines), encoding="utf-8")


if __name__ == "__main__":
    apply_edits(json.loads(Path(sys.argv[1]).read_text()), sys.argv[2], Path(sys.argv[3]))
# === wha-file tools/extract_installer.py ===
#!/usr/bin/env python3
"""Extract an official macOS WiiM Home DMG without executing it."""
import shutil, subprocess, sys
from pathlib import Path

def main():
    if len(sys.argv) != 3:
        raise SystemExit("usage: extract_installer.py <official-dmg> <destination>")
    source, output = map(lambda value: Path(value).resolve(), sys.argv[1:])
    if not shutil.which("7z"):
        raise SystemExit("Missing 7z. On Arch/Manjaro: sudo pacman -S p7zip")
    shutil.rmtree(output, ignore_errors=True)
    output.mkdir(parents=True)
    result = subprocess.run(
        ["7z", "x", "-y", "-o" + str(output), str(source)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    apps = list(output.glob("**/WiiM Home.app/Contents/MacOS/WiiM Home"))
    if len(apps) != 1:
        raise SystemExit("Could not locate WiiM Home.app in official DMG (7z status %d)" % result.returncode)
    print(apps[0])

if __name__ == "__main__":
    main()
# === wha-file tools/rebuild_qt_resources.py ===
#!/usr/bin/env python3
"""Rebuild the PyQt resource module from the patched runtime QML tree."""
import importlib
import os
import py_compile
import shutil
import subprocess
import sys
from pathlib import Path
from xml.sax.saxutils import escape

from PyQt6.QtCore import QDir, QFile, QIODevice


def resource_paths(directory=":/"):
    paths = []
    qdir = QDir(directory)
    flags = QDir.Filter.NoDotAndDotDot | QDir.Filter.AllEntries
    for name in qdir.entryList(flags, QDir.SortFlag.Name):
        resource_path = directory + "/" + name
        if QDir(resource_path).exists():
            paths.extend(resource_paths(resource_path))
        else:
            paths.append(resource_path)
    return paths


def relative_resource_path(resource_path):
    return resource_path[3:] if resource_path.startswith("://") else resource_path[2:]


def source_path(app, relative_path):
    if relative_path.startswith("qml/"):
        return app / "Qml" / relative_path[4:]
    return app / relative_path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: rebuild_qt_resources.py <app-dir>")
    app = Path(sys.argv[1]).resolve()
    resource_dir = app / "resources"
    sys.path.insert(0, str(resource_dir))
    importlib.import_module("app_rc")

    staging = resource_dir / ".qrc-rebuild"
    shutil.rmtree(staging, ignore_errors=True)
    staging.mkdir()
    qrc_entries = []
    for qrc_path in resource_paths():
        relative = relative_resource_path(qrc_path)
        source = source_path(app, relative)
        if not source.is_file():
            source = staging / relative
            source.parent.mkdir(parents=True, exist_ok=True)
            resource_file = QFile(qrc_path)
            if not resource_file.open(QIODevice.OpenModeFlag.ReadOnly):
                raise RuntimeError("cannot read original resource: %s" % qrc_path)
            source.write_bytes(bytes(resource_file.readAll()))
        qrc_entries.append((relative, source))

    qrc_file = staging / "app.qrc"
    lines = ["<RCC><qresource prefix=\"/\">"]
    for relative, source in qrc_entries:
        lines.append('<file alias="%s">%s</file>' % (escape(relative), escape(str(source))))
    lines.append("</qresource></RCC>")
    qrc_file.write_text("\n".join(lines) + "\n", encoding="utf-8")

    generated = staging / "app_rc.py"
    subprocess.run([os.environ.get("RCC", "rcc"), "-g", "python", "-o", str(generated), str(qrc_file)], check=True)
    source_text = generated.read_text(encoding="utf-8").replace("from PySide2 import QtCore", "from PyQt6 import QtCore")
    source_text = source_text.replace("from PySide6 import QtCore", "from PyQt6 import QtCore")
    generated.write_text(source_text, encoding="utf-8")
    py_compile.compile(str(generated), cfile=str(resource_dir / "app_rc.pyc"), doraise=True)
    shutil.rmtree(staging)


if __name__ == "__main__":
    main()
# === wha-file tools/unpack_pyz.py ===
#!/usr/bin/env python3
"""Extract a PyInstaller PYZ into normal Python 3.9 .pyc paths."""
import pathlib, sys
from PyInstaller.archive.readers import CArchiveReader, ZlibArchiveReader

PY39_MAGIC = b'\x61\x0d\x0d\x0a' + b'\0' * 12
source, target = map(pathlib.Path, sys.argv[1:3])
carchive = CArchiveReader(str(source))
main = carchive.extract('main')
(target / 'main.pyc').parent.mkdir(parents=True, exist_ok=True)
(target / 'main.pyc').write_bytes(main if main.startswith(b'\x61\x0d\x0d\x0a') else PY39_MAGIC + main)
pyz_path = target.parent / 'PYZ-00.pyz'
pyz_path.parent.mkdir(parents=True, exist_ok=True)
pyz_path.write_bytes(carchive.extract('PYZ-00.pyz'))
pyz = ZlibArchiveReader(str(pyz_path), check_pymagic=False)
for name, entry in pyz.toc.items():
    data = pyz.extract(name, raw=True)
    if data is None:
        continue
    typecode = entry[0]
    rel = name.replace('.', '/')
    out = target / rel / '__init__.pyc' if typecode == 1 else target / (rel + '.pyc')
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data if data.startswith(b'\x61\x0d\x0d\x0a') else PY39_MAGIC + data)
print(f'extracted {len(pyz.toc)} modules to {target}')
# === wha-file tools/verify_qrc.py ===
#!/usr/bin/env python3
"""Verify that patched QML is in the compiled qrc module actually loaded at run time."""
import sys
from pathlib import Path

from PyQt6.QtCore import QFile, QIODevice


def read_resource(path):
    resource = QFile(path)
    if not resource.open(QIODevice.OpenModeFlag.ReadOnly):
        raise SystemExit("missing qrc resource: %s" % path)
    return bytes(resource.readAll()).decode("utf-8")


def main(app_dir):
    app_dir = Path(app_dir)
    sys.path.insert(0, str(app_dir / "resources"))
    import app_rc

    home = read_resource(":/qml/Tidal/pages/TidalHome.qml")
    collection = read_resource(":/qml/Tidal/pages/TidalCollection.qml")
    grid = read_resource(":/qml/Tidal/sections/TidalHomeTrackGridSection.qml")
    required = (
        (home, "tidalHomeState.isInitialLoading", "TIDAL Home loading binding"),
        (collection, "tidalCollectionState.revision", "Collection revision binding"),
        (grid, "root.itemsModel.rowCount", "Collection model row-count binding"),
    )
    for content, expression, description in required:
        if expression not in content:
            raise SystemExit("qrc verification failed: missing %s" % description)
    if "root.itemsModel.count !== undefined" in grid:
        raise SystemExit("qrc verification failed: obsolete presentation count fallback")
    print("qrc patched-expression verification: PASS")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_qrc.py APP_DIR")
    main(sys.argv[1])
WHA_FILES
