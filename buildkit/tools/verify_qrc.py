#!/usr/bin/env python3
"""Verify that patched QML is in the compiled qrc module actually loaded at run time."""
import sys
from pathlib import Path

from qt_compat.QtCore import QFile, QIODevice


def read_resource(path):
    resource = QFile(path)
    if not resource.open(QIODevice.OpenModeFlag.ReadOnly):
        raise SystemExit("missing qrc resource: %s" % path)
    return bytes(resource.readAll()).decode("utf-8")


def main(app_dir):
    app_dir = Path(app_dir)
    sys.path.insert(0, str(app_dir / "resources"))
    import app_rc  # noqa: F401 - registers qrc:/qml resources

    home = read_resource(":/qml/Tidal/pages/TidalHome.qml")
    collection = read_resource(":/qml/Tidal/pages/TidalCollection.qml")
    grid = read_resource(":/qml/Tidal/sections/TidalHomeTrackGridSection.qml")
    required = (
        (home, "tidalHomeState.isInitialLoading", "TIDAL Home loading binding"),
        (collection, "tidalCollectionState.revision", "Collection revision binding"),
        (grid, "root.itemsModel.rowCount", "Collection model row-count binding"),
    )
    for content, expression, description in required:
        if expression not in content:
            raise SystemExit("qrc verification failed: missing %s" % description)
    if "root.itemsModel.count !== undefined" in grid:
        raise SystemExit("qrc verification failed: obsolete presentation count fallback")
    print("qrc patched-expression verification: PASS")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_qrc.py APP_DIR")
    main(sys.argv[1])
