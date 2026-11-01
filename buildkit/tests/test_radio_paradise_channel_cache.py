#!/usr/bin/env python3
"""Exercise Radio Paradise's original channel-list cache branch with 1.0.1."""
import os
import sys
import tempfile
from pathlib import Path

import requests_cache

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dist/WiiM-Home-Linux/app"
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".test-cache"))
os.environ.setdefault("XDG_CONFIG_HOME", str(ROOT / ".test-config"))
os.environ.setdefault("XDG_DATA_HOME", str(ROOT / ".test-data"))
os.environ.setdefault("BEETSDIR", str(ROOT / ".test-config" / "beets"))
sys.path.append(str(APP))
os.chdir(APP)
import LPGlobalUI
from LPClientFramework.LPDataModel.NetWorkDataModel import LPRadioParadise2NetworkDataModel as module


class Signal:
    def __init__(self):
        self.count = 0

    def emit(self):
        self.count += 1


class Model:
    channelUrlFormatter = "https://api.radioparadise.com/api/list_chan?C_user_id={}"

    def __init__(self, session):
        self.session = session
        self.worker = object()
        self.loadSkeletonSignal = Signal()
        self.calls = []

    def getData(self, worker, url, callback):
        self.calls.append((worker, url, callback))


with tempfile.TemporaryDirectory() as directory:
    model = Model(requests_cache.CachedSession(cache_name=directory + "/radio-paradise", backend="sqlite"))
    callback = object()
    module.LPRadioParadise2NetworkDataModel.fetchChannelData(model, "device-user", callback)
    assert model.loadSkeletonSignal.count == 1
    assert model.calls == [(model.worker, "https://api.radioparadise.com/api/list_chan?C_user_id=device-user", callback)]
    model.session.cache.close()
print("Radio Paradise channel cache path: PASS")
