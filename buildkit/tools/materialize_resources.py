"""Recover editable QML from the official qrc if loose QML is no longer shipped."""
import importlib
import sys
from pathlib import Path
from qt_compat.QtCore import QFile, QIODevice
from rebuild_qt_resources import resource_paths, relative_resource_path


def materialize(app):
    sys.path.insert(0, str(app / "resources"))
    importlib.import_module("app_rc")
    count = 0
    for name in resource_paths():
        relative = relative_resource_path(name)
        if not relative.startswith("qml/"):
            continue
        parts = Path(relative[4:]).parts
        if not parts or ".." in parts:
            raise ValueError("Unsafe qrc path: " + relative)
        target = app / "Qml" / Path(*parts)
        if target.exists():
            continue
        source = QFile(name)
        if not source.open(QIODevice.OpenModeFlag.ReadOnly):
            raise ValueError("Cannot read embedded QML: " + name)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(bytes(source.readAll()))
        count += 1
    if not (app / "Qml/Tidal/pages/TidalCollection.qml").is_file():
        raise ValueError("No supported TIDAL QML resource tree; review required")
    print("Materialized %d embedded QML resources" % count)


if __name__ == "__main__":
    materialize(Path(sys.argv[1]).resolve())
