"""Exercise both original WiiM X-button callbacks with the Linux launch policy."""
import os
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dist/WiiM-Home-Linux/app"
sys.path.insert(0, str(ROOT / "linux"))
sys.path.append(str(APP))
os.chdir(APP)
import LPGlobalUI
from HOME.LPTitleBar import LPTitleBar
from HOME.WiiMHome import LPDeviceSearchingViewController
from app_icon import configure_window_close

previous = LPGlobalUI.mainWindow
try:
    for option in (None, "1", "0"):
        if option is None:
            os.environ.pop("WIIM_HIDE_TO_TRAY", None)
        else:
            os.environ["WIIM_HIDE_TO_TRAY"] = option
        for callback in (LPTitleBar.onCloseButtonClicked,
                         LPDeviceSearchingViewController._closeWindowFromQml):
            calls = []
            window = SimpleNamespace(enableMemoryResident=True,
                                     hide=lambda: calls.append("hide"),
                                     quitApp=lambda: calls.append("quit"))
            configure_window_close(window)
            LPGlobalUI.mainWindow = window
            callback(None)
            assert calls == (["hide"] if option == "1" else ["quit"]), (option, calls)
finally:
    LPGlobalUI.mainWindow = previous
print("Original titlebar and searching-page X: quit default / hide opt-in: PASS")
