#!/usr/bin/env python3
"""Exercise the installed Preset worker callback with a device-shaped reply."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dist/WiiM-Home-Linux/app"
os.chdir(APP)
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".test-cache"))
os.environ.setdefault("XDG_CONFIG_HOME", str(ROOT / ".test-config"))
os.environ.setdefault("XDG_DATA_HOME", str(ROOT / ".test-data"))
Path(os.environ["XDG_CACHE_HOME"]).joinpath("com.linkplay.wiimhome").mkdir(parents=True, exist_ok=True)
Path(os.environ["XDG_CONFIG_HOME"]).joinpath("com.linkplay.wiimhome").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("BEETSDIR", str(ROOT / ".test-config" / "beets"))
Path(os.environ["BEETSDIR"]).mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "linux"))
sys.path.append(str(APP))

import LPGlobalUI
from preset_fix import install_preset_fix

install_preset_fix()
from HOME import LPPresetViewController as preset_module

class Signal:
    def __init__(self): self.count = 0
    def emit(self): self.count += 1

class Device:
    presetNum = 3
    def asyncUpnpPost(self, command, params, callback):
        assert command == "GetKeyMapping" and params == {}
        callback({"status_code": 200, "xml": "<KeyList><Key1><Name>Radio</Name><Source>newTuneIn</Source></Key1><Key2/></KeyList>"})

class View:
    updateUISignal = Signal()

LPGlobalUI.currentDevice = Device()
view = View()
preset_module.LPPresetViewController._fetchPresetList(view)
assert view.status == preset_module.LPPresetViewControllerState.ready
assert [item.name for item in view.presetList] == ["Radio", "", ""]
assert view.updateUISignal.count == 1
print("GetKeyMapping callback: PASS")
