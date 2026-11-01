#!/usr/bin/env python3
"""Exercise the actual observer HTTP server through repeated bind/stop cycles."""
import os
import socket
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "dist/WiiM-Home-Linux/app"
os.environ.setdefault("XDG_CACHE_HOME", str(ROOT / ".test-cache"))
os.environ.setdefault("XDG_CONFIG_HOME", str(ROOT / ".test-config"))
os.environ.setdefault("XDG_DATA_HOME", str(ROOT / ".test-data"))
sys.path.append(str(ROOT / "linux"))
sys.path.append(str(APP))

os.chdir(APP)
import LPGlobalUI
from observer_lifecycle_fix import _transport_summary, install_observer_lifecycle_fix
from single_instance import reserve_observer_port
from LPClientFramework.LPUPnPObserverManager import LPUPnPObserverManager
modern = hasattr(LPUPnPObserverManager, "_maintainSubscriptions")
original_start, original_stop = LPUPnPObserverManager.start, LPUPnPObserverManager.stop
install_observer_lifecycle_fix()
if modern:
    assert LPUPnPObserverManager.start is original_start
    assert LPUPnPObserverManager.stop is original_stop

summary = _transport_summary({"playState": "PLAYING", "duration": "00:05:00", "playUri": "https://signed.example/token", "trackId": "1"})
assert summary == {"playState": "PLAYING", "duration": "00:05:00", "trackId": "1", "hasTrackUri": True}


def free_port():
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return probe.getsockname()[1]


manager = LPUPnPObserverManager(lambda *_args: None)
manager.port = free_port()
for _ in range(3):
    assert manager.start() is True
    for _ in range(20):
        try:
            with socket.create_connection(("127.0.0.1", manager.port), timeout=0.1):
                break
        except OSError:
            time.sleep(0.05)
    else:
        raise AssertionError("observer did not accept connections")
    timeout_thread = manager.timeoutThread
    manager.stop()
    if modern:
        assert manager._stopEvent.is_set()
        assert not timeout_thread.is_alive()
    with socket.socket() as probe:
        # Match the real listener's address-reuse policy: accepted connections
        # may still be in TIME_WAIT even after every server socket is closed.
        # This does not allow a second listener (SO_REUSEPORT remains off).
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        probe.bind(("", manager.port))

# The listener claimed before application initialization is adopted by the
# observer server, so no second bind race can leave subscriptions half alive.
reserved_port = free_port()
reserve_observer_port(reserved_port)
reserved_manager = LPUPnPObserverManager(lambda *_args: None)
reserved_manager.port = reserved_port
assert reserved_manager.start() is True
assert reserved_manager.httpServer.server_address[1] == reserved_port
reserved_manager.stop()

# The occupied fixed-port case is reported synchronously; it must not become
# an unhandled exception in the daemon server thread.
occupied_port = free_port()
with socket.socket() as blocker:
    blocker.bind(("", occupied_port))
    blocker.listen()
    blocked_manager = LPUPnPObserverManager(lambda *_args: None)
    blocked_manager.port = occupied_port
    assert blocked_manager.start() is False
    if modern:
        assert blocked_manager.serverSwitch is False
        assert blocked_manager.serverThread is None
    else:
        assert blocked_manager.observerBindError.errno == 98
print("UPnP observer lifecycle: PASS")
