"""Linux replacement for the small macOS/Windows crash-handler adapter.

The WiiM application itself already selects a no-op native handler on Linux;
this adapter supplies its writable crash directory using XDG state/data paths.
"""
import datetime
import faulthandler
import os
import traceback

def get_crash_dir():
    base = os.environ.get("XDG_STATE_HOME") or os.environ.get("XDG_DATA_HOME")
    if not base:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    path = os.path.join(base, "WiiMHome", "crashes")
    os.makedirs(path, exist_ok=True)
    return path

def install_native_crash_handler():
    return None

def generate_crash_timestamp():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

def _write_python_traceback_simple(dump_path=None):
    path = os.path.join(get_crash_dir(), "python_%s.log" % generate_crash_timestamp())
    with open(path, "w", encoding="utf-8") as stream:
        traceback.print_exc(file=stream)
        faulthandler.dump_traceback(file=stream)
    return path
