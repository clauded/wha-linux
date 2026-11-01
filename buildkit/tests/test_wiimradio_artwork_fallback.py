#!/usr/bin/env python3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "linux"))
from wiimradio_artwork_fallback import WiiMRadioArtworkFallback


class Pixmap:
    def __init__(self, valid=True): self.valid = valid
    def isNull(self): return not self.valid


class Media:
    trackSource = "WiiMRadio"; playState = "PLAYING"; trackId = "station-91-4"
    playUri = "https://radio.example/stream"; artworkImage = None


class Device:
    uuid = "test-device"; mediaInfo = Media()


loaded = []
fallback = WiiMRadioArtworkFallback(lambda source: loaded.append(source) or Pixmap())
device = Device()
station = {"stationId": "station-91-4", "streamUrl": "https://radio.example/stream", "faviconThumbPath": "/cache/station.png"}
fallback.remember_station(device, station)
assert fallback.reconcile(device) is True and loaded == ["/cache/station.png"]
device.mediaInfo.artworkImage = Pixmap()
assert fallback.reconcile(device) is False
device.mediaInfo.artworkImage = None; device.mediaInfo.trackId = "other-station"
assert fallback.reconcile(device) is False
fallback.remember_station(device, station)
device.mediaInfo.trackId = "station-91-4"; device.mediaInfo.playState = "STOPPED"
assert fallback.reconcile(device) is False and fallback._records == {}
print("WiiM Radio artwork fallback: PASS")
