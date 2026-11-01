"""Narrow protocol validation for WiiM's asynchronous preset mapping reply."""
import re
from bs4 import BeautifulSoup


class PresetProtocolError(ValueError):
    pass


def _redacted_xml_for_log(xml_text):
    """Keep protocol diagnostics useful without exposing credential-shaped values."""
    redacted = re.sub(
        r"(?is)<(access_?token|refresh_?token|token|password|authorization)[^>]*>.*?</\1\s*>",
        r"<\1>[redacted]</\1>",
        xml_text,
    )
    redacted = re.sub(r"(?i)(access_?token|refresh_?token|token|password)=([^&\s<'\"]+)", r"\1=[redacted]", redacted)
    return redacted[:2048]


def parse_key_mapping(xml_text, preset_count):
    """Return slot maps from a valid GetKeyMapping QueueContext XML payload."""
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
    """Replace only the upstream callback that dereferenced a missing KeyList."""
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
