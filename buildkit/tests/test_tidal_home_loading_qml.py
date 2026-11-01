#!/usr/bin/env python3
"""Regression: TidalHome's content Loader must follow isInitialLoading."""
import os
import sys
from pathlib import Path

from qt_compat.QtCore import QObject, pyqtProperty, pyqtSignal, pyqtSlot, QUrl
from qt_compat.QtGui import QGuiApplication
from qt_compat.QtQml import QQmlApplicationEngine

ROOT = Path(__file__).resolve().parents[1]
QML = ROOT / "dist/WiiM-Home-Linux/app/Qml/Tidal/pages/TidalHome.qml"
sys.path.insert(0, str(QML.parents[3] / "resources"))
import app_rc  # Register the compiled resources actually used by the app.

class HomeState(QObject):
    isInitialLoadingChanged = pyqtSignal()
    sectionDataChanged = pyqtSignal()
    def __init__(self):
        super().__init__(); self._loading = True
    @pyqtProperty(bool, notify=isInitialLoadingChanged)
    def isInitialLoading(self): return self._loading
    def set_loading(self, value):
        self._loading = value; self.isInitialLoadingChanged.emit()
    @pyqtSlot(str, result="QVariant")
    def sectionInfo(self, _): return {}
    @pyqtSlot(int, result="QVariant")
    def sectionInfoAt(self, _): return {}
    @pyqtSlot(result=int)
    def sectionCount(self): return 0

class Store(QObject):
    accountStateChanged = pyqtSignal()
    @pyqtProperty("QVariant")
    def accountState(self): return {}
    @pyqtProperty(QObject)
    def collectionState(self): return None

def loader_item_classes(root):
    classes = []
    for child in root.findChildren(QObject):
        if child.metaObject().className() == "QQuickLoader":
            item = child.property("item")
            if item is not None:
                classes.append(item.metaObject().className())
    return classes

app = QGuiApplication([])
engine = QQmlApplicationEngine()
state, store = HomeState(), Store()
ctx = engine.rootContext()
ctx.setContextProperty("tidalHomeActions", None)
ctx.setContextProperty("tidalStore", store)
engine.load(QUrl("qrc:/qml/Tidal/pages/TidalHome.qml"))
assert engine.rootObjects(), "TidalHome failed to load"
root = engine.rootObjects()[0]
root.setProperty("tidalHomeState", state)
app.processEvents()
assert any("ScrollView" in name for name in loader_item_classes(root)), loader_item_classes(root)
state.set_loading(False)
app.processEvents()
app.processEvents()
assert any("ListView" in name for name in loader_item_classes(root)), loader_item_classes(root)
print("TidalHome Loader follows isInitialLoading: PASS")
