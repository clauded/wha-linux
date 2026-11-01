"""Bridge WiiM Radio's locally cached station art into device media state."""
import logging


_SOURCE = "WiiMRadio"
_STOPPED = "STOPPED"


def _text(value):
    return str(value or "").strip()


def _is_valid_pixmap(pixmap):
    return pixmap is not None and not pixmap.isNull()


def _local_pixmap(source):
    """Load only the thumbnail resource already prepared for the catalog."""
    from qt_compat.QtCore import QUrl
    from qt_compat.QtGui import QPixmap

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
    """Maintain transient selected-station art keyed by the actual device."""

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
        """Install art only for current WiiM Radio media with no device art."""
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
    """Patch only station selection and device MediaInfo update boundaries."""
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
