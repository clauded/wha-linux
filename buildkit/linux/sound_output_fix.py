"""Normalize WiiM USB audio-output records for the original sound-settings UI."""
import logging


_UAC_MODE = "AUDIO_OUTPUT_UAC_CARD_MODE"


def _entry_shape(entry):
    """Return protocol structure only; names and device identifiers stay out of logs."""
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
    """Promote the UAC device identity supplied by current WiiM firmware.

    The original UI reads ``item['devName']`` for the active USB output, while
    ``getSoundCardModeSupportList`` supplies that name under ``soundCard``.
    An incomplete active USB record is withheld rather than inventing a name.
    """
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
            # The upstream UI must dereference devName for the active UAC row.
            # This is not a selectable/renderable USB endpoint until firmware
            # supplies either the support-list or active-output identity.
            if logger is not None:
                logger.warning("[SoundOutput] withholding incomplete active UAC output: %s", _entry_shape(item))
            continue
        normalized.append(item)
    return normalized


def install_sound_output_fix():
    """Patch only the original UI boundary immediately before its devName access."""
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
