"""Give the native Qt application a stable GNOME identity and WiiM icon."""
import os
import logging
import shlex
from pathlib import Path


_APP_ID = "wiim-home-linux"
_APP_NAME = "WiiM Home"

def configure_window_close(window):
    """Use WiiM's existing X-button route; do not rewrite saved preferences."""
    window.enableMemoryResident = os.environ.get("WIIM_HIDE_TO_TRAY") == "1"

def icon_path(app_root=None):
    """Return the official multi-resolution WiiM icon shipped by the input."""
    root = Path(app_root or os.environ["WIIM_HOME_APP"])
    return root / "images" / "app.ico"


def desktop_entry_path(app_root=None):
    """Use GNOME's user application directory, not the bundle's private data."""
    root = Path(app_root or os.environ["WIIM_HOME_APP"]).resolve()
    configured = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share")).resolve()
    if configured == root.parent / "data" or root in configured.parents:
        configured = Path.home() / ".local" / "share"
    return configured / "applications" / (_APP_ID + ".desktop")


def desktop_entry_text(app_root=None):
    root = Path(app_root or os.environ["WIIM_HOME_APP"]).resolve()
    # Reproducer output has run.sh beside app/, while the development build
    # launches through the repository-level wrapper.
    launcher = root.parent / "run.sh"
    if not launcher.is_file():
        launcher = root.parent.parent.parent / "run.sh"
    icon = root / "images" / "ico.png"
    content = """[Desktop Entry]\nType=Application\nName=%s\nGenericName=Audio Control Center\nComment=Control WiiM devices\nExec=%s\nIcon=%s\nTerminal=false\nCategories=AudioVideo;Audio;Player;Qt;\nStartupWMClass=%s\nStartupNotify=true\n""" % (_APP_NAME, shlex.quote(str(launcher)), str(icon), _APP_ID)
    desktops = os.environ.get("XDG_CURRENT_DESKTOP", "").upper().split(":")
    if "KDE" in desktops or "PLASMA" in desktops:
        content += "X-KDE-Wayland-AppID=%s\n" % _APP_ID
    # Do not force a Plasma theme or native frame on GNOME (or load a system
    # Qt plugin into a differently versioned wheel's Qt runtime).
    return content


def ensure_desktop_entry(app_root=None):
    path = desktop_entry_path(app_root)
    content = desktop_entry_text(app_root)
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            if path.read_text(encoding="utf-8") == content:
                return path
        except FileNotFoundError:
            pass
        path.write_text(content, encoding="utf-8")
        return path
    except OSError as error:
        logging.getLogger(__name__).warning("Desktop integration unavailable: %s", error)
        return None


def configure_application(application):
    """Set Wayland/X11 metadata before the first top-level window maps."""
    application.setApplicationName(_APP_NAME)
    if hasattr(application, "setApplicationDisplayName"):
        application.setApplicationDisplayName(_APP_NAME)
    if hasattr(application, "setDesktopFileName"):
        application.setDesktopFileName(_APP_ID)
    return ensure_desktop_entry()


def install_app_icon():
    """Install app metadata and icon before the main window becomes visible."""
    from qt_compat.QtGui import QIcon
    from qt_compat.QtWidgets import QApplication
    from HOME import LPApplication as application_module
    from HOME import WiiMHome as home_module

    application_class = application_module.LPApplication
    window_class = home_module.LPStreamServiceMainWindow
    if getattr(window_class, "_linux_app_icon_installed", False):
        return
    original_setup = window_class.setupUi
    original_application_init = application_class.__init__
    original_window_init = window_class.__init__

    def window_init(self, *args, **kwargs):
        result = original_window_init(self, *args, **kwargs)
        configure_window_close(self)
        return result

    def application_init(self, *args, **kwargs):
        result = original_application_init(self, *args, **kwargs)
        configure_application(self)
        return result

    def setup_ui(self, *args, **kwargs):
        result = original_setup(self, *args, **kwargs)
        # Loading an .ico creates QPixmaps; Qt requires QApplication first.
        path = icon_path()
        icon = QIcon(str(path))
        if icon.isNull():
            logging.getLogger(__name__).warning("WiiM application icon is unavailable: %s", path)
            return result
        application = QApplication.instance()
        if application is not None:
            application.setWindowIcon(icon)
        self.setWindowIcon(icon)
        return result

    application_class.__init__ = application_init
    window_class.__init__ = window_init
    window_class.setupUi = setup_ui
    window_class._linux_app_icon_installed = True
