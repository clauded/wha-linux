#!/usr/bin/env python3
"""Regression coverage for valid, empty, and malformed preset mappings."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "linux"))
from preset_fix import PresetProtocolError, parse_key_mapping

valid = """<KeyList><Key1><Name>Station</Name><Source>newTuneIn</Source><PicUrl>https://example.invalid/a.png</PicUrl></Key1><Key2/></KeyList>"""
slots = parse_key_mapping(valid, 3)
assert len(slots) == 3
assert slots[0] == {"index": 1, "name": "Station", "source": "newTuneIn", "picUrl": "https://example.invalid/a.png"}
assert slots[1] == {"index": 2, "name": "", "source": "", "picUrl": ""}
assert slots[2]["index"] == 3
assert len(parse_key_mapping("<KeyList/>", 2)) == 2
try:
    parse_key_mapping("<UnexpectedResponse/>", 2)
except PresetProtocolError:
    pass
else:
    raise AssertionError("missing KeyList must be a visible protocol error, not a crash")
print("GetKeyMapping parser: PASS")
