"""Binding-neutral imports for OUR adapters/tests, never alias vendor modules."""
import importlib
import os

BINDING = os.environ.get("WIIM_QT_BINDING", "PyQt6")
if BINDING not in ("PyQt6", "PySide6"):
    raise RuntimeError("Unsupported Qt binding: " + BINDING)


def export(name, namespace):
    module = importlib.import_module(BINDING + "." + name)
    namespace.update((key, getattr(module, key)) for key in dir(module) if not key.startswith("__"))
    if name == "QtCore" and BINDING == "PySide6":
        for alias, original in (("pyqtSignal", "Signal"), ("pyqtProperty", "Property"), ("pyqtSlot", "Slot")):
            namespace[alias] = getattr(module, original)
