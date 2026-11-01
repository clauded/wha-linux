#!/usr/bin/env python3
"""Run the real app's X callbacks in a private network namespace, then rebind ports.

Usage: python3 tools/test_close_runtime.py /absolute/build/out/WiiM-Home-Linux
No test hooks are included in the distributed launcher.
"""
import os
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile


def child(bundle, mode):
    import runpy
    import sysconfig
    import time
    os.chdir(bundle / "app")
    sys.path[:0] = [str(bundle), sysconfig.get_paths()["purelib"], str(bundle / "app")]
    from qt_compat.QtWidgets import QApplication
    from qt_compat.QtCore import QTimer
    original_exec = QApplication.exec

    def execute(app):
        import LPGlobalUI
        import cherrypy
        window = LPGlobalUI.mainWindow
        assert window.enableMemoryResident == (mode == "hide")
        deadline = time.monotonic() + 15

        def finish_hide():
            assert not window.isVisible() and not window._isQuitting
            with socket.create_connection(("127.0.0.1", 22334), timeout=1):
                pass
            window.showApp()
            assert window.isVisible()
            print("HIDDEN_AND_RESTORED", flush=True)
            window.quitApp()

        def click():
            if cherrypy.engine.state != cherrypy.engine.states.STARTED:
                assert time.monotonic() < deadline, "local services never started"
                QTimer.singleShot(100, click)
                return
            assert window.isVisible()
            print("CLICK_X_" + mode, flush=True)
            if mode == "hide":
                QTimer.singleShot(250, finish_hide)
            # Invoke the real titlebar slot wired to its X button.
            window.titleBar.onCloseButtonClicked()

        QTimer.singleShot(0, click)
        return original_exec()

    QApplication.exec = execute
    runpy.run_path(str(bundle / "bootstrap.py"), run_name="__main__")


def inside(bundle):
    with tempfile.TemporaryDirectory(prefix="wiim-close-test-") as tmp:
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen", QT_QUICK_BACKEND="software",
                   PYTHONNOUSERSITE="1", WIIM_HOME_APP=str(bundle / "app"),
                   WIIM_HOME_RESOURCES=str(bundle / "resources"))
        env["WIIM_QT_BINDING"] = json.loads((bundle / "build-metadata.json").read_text())["qt_binding"]
        env.pop("PYTHONHOME", None)
        env.pop("PYTHONPATH", None)
        for kind in ("DATA", "CONFIG", "CACHE"):
            env["XDG_" + kind + "_HOME"] = str(Path(tmp) / kind.lower())
            Path(env["XDG_" + kind + "_HOME"]).mkdir()
        env["XDG_RUNTIME_DIR"] = str(Path(tmp) / "runtime")
        Path(env["XDG_RUNTIME_DIR"]).mkdir(mode=0o700)
        env["BEETSDIR"] = str(Path(tmp) / "beets")
        Path(env["BEETSDIR"]).mkdir()
        for mode in ("quit", "hide", "quit", "quiet"):
            env["WIIM_HIDE_TO_TRAY"] = "1" if mode == "hide" else "0"
            env["WIIM_DEBUG"] = "0" if mode == "quiet" else "1"
            try:
                process = subprocess.run([sys.executable, __file__, "--child", str(bundle), mode],
                                         env=env, capture_output=True, text=True, timeout=25)
            except subprocess.TimeoutExpired as error:
                print(((error.stdout or b"") + (error.stderr or b"")).decode(errors="replace")[-6000:])
                raise
            log = process.stdout + process.stderr
            vendor_watchdog = (process.returncode == -9
                               and "[quit] watchdog forced kill on non-windows" in log)
            assert process.returncode == 0 or vendor_watchdog, log[-6000:]
            assert "CLICK_X_" + mode in log, log[-6000:]
            if mode == "quiet":
                assert "[DEBUG]" not in log and "[INFO ]" not in log, log[-6000:]
                assert "[collection-debug]" not in log, log[-6000:]
            if mode == "hide":
                assert "HIDDEN_AND_RESTORED" in log, log[-6000:]
            assert "[Global Exception Capture]" not in log, log[-6000:]
            for port in (22334, 22345, 22346, 22347):
                with socket.socket() as probe:
                    probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    probe.bind(("0.0.0.0", port))
            termination = "original WiiM watchdog" if vendor_watchdog else "normal exit"
            print("Real X mode=%s: process exited (%s); all four ports released: PASS" % (mode, termination), flush=True)


if __name__ == "__main__":
    if sys.argv[1] == "--child":
        child(Path(sys.argv[2]), sys.argv[3])
    elif sys.argv[1] == "--inside":
        inside(Path(sys.argv[2]))
    else:
        bundle = Path(sys.argv[1]).resolve()
        setup = ('set -e; ip link set lo up; ip link add wha-test type dummy; '
                 'ip addr add 192.0.2.2/24 dev wha-test; ip link set wha-test up; '
                 'ip route add default via 192.0.2.1; exec "$@"')
        subprocess.run(["unshare", "--user", "--map-root-user", "--net", "sh", "-c", setup,
                        "sh", str(bundle / "runtime/venv/bin/python"),
                        str(Path(__file__).resolve()), "--inside", str(bundle)], check=True)
