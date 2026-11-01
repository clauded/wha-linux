"""Native launcher compatibility flags for PyInstaller-reconstructed code."""
import os
import runpy
import sys

app = os.environ["WIIM_HOME_APP"]
from single_instance import AlreadyRunning, ObserverPortUnavailable, acquire, install_signal_cleanup, reserve_observer_port
try:
    _instance_lock = acquire()
except AlreadyRunning as error:
    print("WiiM Home: %s" % error, file=sys.stderr)
    raise SystemExit(2)
install_signal_cleanup()
try:
    reserve_observer_port()
except ObserverPortUnavailable as error:
    print("WiiM Home: %s" % error, file=sys.stderr)
    raise SystemExit(3)
from runtime_options import configure_runtime_options
configure_runtime_options()
# LPGlobalUI uses this flag to choose the original compiled *_ui Python
# classes instead of trying to find unbundled Qt Designer .ui files.
sys.frozen = True
sys._MEIPASS = app
from preset_fix import install_preset_fix
from sound_output_fix import install_sound_output_fix
from cache_compat import ensure_http_cache_compatibility
install_preset_fix()
install_sound_output_fix()
ensure_http_cache_compatibility(os.environ["XDG_CACHE_HOME"] + "/com.linkplay.wiimhome")
# Keep the upstream import order required by LPUtility and the observer.
import LPGlobalUI
from observer_lifecycle_fix import install_observer_lifecycle_fix
install_observer_lifecycle_fix()
from wiimradio_artwork_fallback import install_wiimradio_artwork_fallback
install_wiimradio_artwork_fallback()
from app_icon import install_app_icon
install_app_icon()
runpy.run_path(os.path.join(app, "main.pyc"), run_name="__main__")
