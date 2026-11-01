#!/usr/bin/env python3
"""Regression coverage for the observed WiiM USB sound-card response shape."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "linux"))

from sound_output_fix import normalize_audio_outputs


UAC = object()
observed_uac = {
    "index": 5,
    "mode": "AUDIO_OUTPUT_UAC_CARD_MODE",
    "type": UAC,
    "title": "USB Out",
    "soundCard": {
        "cardName": "USB DAC",
        "devName": "USB DAC device identity",
    },
}

result = normalize_audio_outputs([observed_uac], UAC, None)
assert result == [observed_uac]
assert observed_uac["devName"] == "USB DAC device identity"

# Do not fabricate an empty identity: an incomplete active USB endpoint is not
# renderable by the unmodified original UI and must wait for a complete reply.
incomplete = {"mode": "AUDIO_OUTPUT_UAC_CARD_MODE", "type": UAC, "soundCard": {"cardName": "USB DAC"}}
assert normalize_audio_outputs([incomplete], UAC, None) == []

# The active-output endpoint is a second legitimate protocol source for the
# same identity while a support-list refresh is incomplete.
fallback = {"mode": "AUDIO_OUTPUT_UAC_CARD_MODE", "type": UAC, "soundCard": {"cardName": "USB DAC"}}
result = normalize_audio_outputs([fallback], UAC, "Active USB DAC")
assert result == [fallback]
assert fallback["devName"] == "Active USB DAC"
print("sound output normalization: PASS")
