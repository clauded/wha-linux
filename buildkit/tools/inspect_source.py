"""Inspect structural compatibility after extraction, before applying patches."""
import json
import marshal
import plistlib
import re
import sys
from pathlib import Path


def inspect(contents, work):
    info = plistlib.loads((contents / "Info.plist").read_bytes())
    metadata = json.loads((work / "archive-metadata.json").read_text())
    metadata.update(version=info["CFBundleShortVersionString"], bundle_build=info["CFBundleVersion"])
    if metadata["qt_binding"] == "PySide6":
        code = marshal.loads((work / "pyz/PySide6/__init__.pyc").read_bytes()[16:])
        versions = [v for v in code.co_consts if isinstance(v, str) and re.fullmatch(r"\d+\.\d+\.\d+", v)]
        if len(versions) != 1 or not versions[0].startswith("6.8."):
            raise ValueError("Unsupported PySide6 series %s; review Linux wheel profile" % versions)
        metadata["source_binding_version"] = versions[0]
    metadata["linux_binding_version"] = "6.8.3" if metadata["qt_binding"] == "PySide6" else "6.10.2"
    metadata["loose_qml"] = (contents / "Resources/Qml").is_dir()
    (work / "source-metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata, sort_keys=True))


if __name__ == "__main__":
    inspect(Path(sys.argv[1]), Path(sys.argv[2]))
