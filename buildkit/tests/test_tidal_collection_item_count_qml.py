#!/usr/bin/env python3
"""Regression: collection QAbstractListModels must not bind grid itemCount to QML count."""
import sys
from pathlib import Path

from qt_compat.QtCore import QFile, QIODevice, QObject, QUrl, pyqtProperty, pyqtSignal, qInstallMessageHandler
from qt_compat.QtGui import QGuiApplication
from qt_compat.QtQml import QQmlApplicationEngine

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dist/WiiM-Home-Linux/app"
QML = APP / "Qml/Tidal/pages/TidalCollection.qml"
sys.path.insert(0, str(APP))
sys.path.insert(0, str(APP / "resources"))

from HOME.StreamService.Tidal.models.LPTidalListModel import LPTidalListModel
import app_rc  # Register the exact qrc:/qml resource used by the application.


def make_model(size=0):
    model = LPTidalListModel()
    model.setItems([
        {"itemId": str(index), "title": "Item %d" % index, "artistName": "Artist"}
        for index in range(size)
    ])
    return model


class CollectionState(QObject):
    collectionDataChanged = pyqtSignal()
    loadingStateChanged = pyqtSignal()
    loadedStateChanged = pyqtSignal()
    errorMessageChanged = pyqtSignal()
    revisionChanged = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.playlists = make_model()
        self.artists = make_model()
        self.albums = make_model()
        self.tracks = make_model()
        self._has_any_content = False
        self._revision = 0

    def populate(self, playlists, artists, albums, tracks):
        for model, size in ((self.playlists, playlists), (self.artists, artists),
                            (self.albums, albums), (self.tracks, tracks)):
            model.setItems([
                {"itemId": str(index), "title": "Item %d" % index, "artistName": "Artist"}
                for index in range(size)
            ])
        self._has_any_content = any((playlists, artists, albums, tracks))
        self._revision += 1
        self.collectionDataChanged.emit()
        self.revisionChanged.emit()

    @pyqtProperty(QObject, notify=collectionDataChanged)
    def userPlaylists(self): return self.playlists

    @pyqtProperty(QObject, notify=collectionDataChanged)
    def favoriteArtists(self): return self.artists

    @pyqtProperty(QObject, notify=collectionDataChanged)
    def favoriteAlbums(self): return self.albums

    @pyqtProperty(QObject, notify=collectionDataChanged)
    def favoriteTracks(self): return self.tracks

    @pyqtProperty(bool, notify=loadingStateChanged)
    def isLoading(self): return False

    @pyqtProperty(bool, notify=loadedStateChanged)
    def hasLoaded(self): return True

    @pyqtProperty(bool, notify=collectionDataChanged)
    def hasAnyContent(self): return self._has_any_content

    @pyqtProperty(str, notify=errorMessageChanged)
    def errorMessage(self): return ""

    @pyqtProperty(int, notify=revisionChanged)
    def revision(self): return self._revision


class Store(QObject):
    accountStateChanged = pyqtSignal()

    @pyqtProperty("QVariant", notify=accountStateChanged)
    def accountState(self): return {"isLoggedIn": True}


warnings = []


def message_handler(_type, _context, message):
    if "Binding loop detected for property \"itemCount\"" in message:
        warnings.append(message)


def section(root, key):
    for child in root.findChildren(QObject):
        if child.property("sectionKey") == key:
            return child
    raise AssertionError("section not found: %s" % key)


def delegate_count(section_object):
    """The primary Track grid Repeater has the largest live delegate count."""
    counts = [child.property("count") for child in section_object.findChildren(QObject)
              if child.metaObject().className() == "QQuickRepeater"]
    return max(counts) if counts else 0


qInstallMessageHandler(message_handler)
app = QGuiApplication([])
grid_resource = QFile(":/qml/Tidal/sections/TidalHomeTrackGridSection.qml")
assert grid_resource.open(QIODevice.OpenModeFlag.ReadOnly)
grid_source = bytes(grid_resource.readAll()).decode("utf-8")
assert "root.itemsModel.rowCount !== undefined" in grid_source
assert "root.itemsModel.count !== undefined" not in grid_source
engine = QQmlApplicationEngine()
engine.addImportPath(str(APP / "Qml"))
state = CollectionState()
store = Store()
engine.rootContext().setContextProperty("tidalCollectionActions", None)
engine.rootContext().setContextProperty("tidalStore", store)
engine.load(QUrl("qrc:/qml/Tidal/pages/TidalCollection.qml"))
assert engine.rootObjects(), "TidalCollection failed to load"
root = engine.rootObjects()[0]
root.setProperty("width", 1200)
root.setProperty("height", 800)
root.setProperty("tidalCollectionState", state)
for _ in range(12):
    app.processEvents()

for key in ("userPlaylists", "favoriteArtists", "favoriteAlbums", "favoriteTracks"):
    assert not section(root, key).property("visible"), "%s should start empty" % key

tracks = section(root, "favoriteTracks")
assert tracks.property("itemCount") == 0, tracks.property("itemCount")
state.populate(35, 10, 10, 49)
for _ in range(12):
    app.processEvents()
for key in ("userPlaylists", "favoriteArtists", "favoriteAlbums", "favoriteTracks"):
    assert section(root, key).property("visible"), "%s did not become visible" % key
assert tracks.property("itemCount") == 49, tracks.property("itemCount")
assert delegate_count(tracks) > 0, "track delegates were not instantiated"
state.populate(35, 10, 10, 7)
for _ in range(12): app.processEvents()
assert tracks.property("itemCount") == 7, tracks.property("itemCount")
state.populate(35, 10, 10, 0)
for _ in range(12): app.processEvents()
assert tracks.property("itemCount") == 0, tracks.property("itemCount")
assert not tracks.property("visible"), "empty Tracks section remained visible"
state.populate(35, 10, 10, 12)
for _ in range(12): app.processEvents()
assert tracks.property("itemCount") == 12, tracks.property("itemCount")
assert tracks.property("visible"), "Tracks section did not become visible again"
assert delegate_count(tracks) > 0, "updated track delegates were not instantiated"
assert not warnings, warnings
print("TidalCollection QAbstractListModel itemCount binding: PASS")
