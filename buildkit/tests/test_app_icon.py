#!/usr/bin/env python3
import sys
import inspect
import os
import tempfile
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "linux"))
from app_icon import desktop_entry_text, ensure_desktop_entry, icon_path, install_app_icon

path = icon_path(ROOT / "out" / "WiiM-Home-Linux" / "app")
assert path.name == "app.ico" and path.is_file()
assert path.read_bytes()[:4] == b"\x00\x00\x01\x00"
assert "*args, **kwargs" in inspect.getsource(install_app_icon)
entry = desktop_entry_text(ROOT / "out" / "WiiM-Home-Linux" / "app")
assert "Name=WiiM Home\n" in entry
assert "StartupWMClass=wiim-home-linux\n" in entry
assert "Exec=%s\n" % (ROOT / "out" / "WiiM-Home-Linux" / "run.sh").resolve() in entry
app = ROOT / "out" / "WiiM-Home-Linux" / "app"
for desktop, kde in (("GNOME", False), ("KDE", True), ("ubuntu:GNOME", False), ("Plasma", True)):
    with patch.dict(os.environ, XDG_CURRENT_DESKTOP=desktop):
        assert ("X-KDE-Wayland-AppID=wiim-home-linux\n" in desktop_entry_text(app)) == kde
with tempfile.TemporaryDirectory() as directory:
    with patch.dict(os.environ, XDG_DATA_HOME=directory):
        desktop = ensure_desktop_entry(app)
        assert desktop.is_file()
        previous = desktop.stat().st_mtime_ns
        assert ensure_desktop_entry(app).stat().st_mtime_ns == previous
        with patch.object(Path, "write_text", side_effect=PermissionError("test: read-only desktop directory")):
            with patch.dict(os.environ, XDG_CURRENT_DESKTOP="KDE"):
                with patch("app_icon.logging.getLogger") as logger:
                    assert ensure_desktop_entry(app) is None
                    logger.return_value.warning.assert_called_once()
print("WiiM Qt application icon: PASS")
