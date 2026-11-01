#!/usr/bin/env python3
"""A second process must fail before it can bind WiiM Home local services."""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_DIR = ROOT / ".test-cache" / "single-instance"
LOCK_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / "linux"))
os.environ["XDG_RUNTIME_DIR"] = str(LOCK_DIR)

from single_instance import acquire

lock = acquire()
command = "from single_instance import acquire, AlreadyRunning;\ntry:\n acquire()\nexcept AlreadyRunning:\n raise SystemExit(2)\nraise SystemExit(1)"
result = subprocess.run(
    [sys.executable, "-c", command],
    env={**os.environ, "PYTHONPATH": str(ROOT / "linux")},
    check=False,
)
bootstrap = ROOT / "dist/WiiM-Home-Linux/bootstrap.py"
bootstrap_result = subprocess.run(
    [sys.executable, str(bootstrap)],
    env={
        **os.environ,
        "WIIM_HOME_APP": str(ROOT / "dist/WiiM-Home-Linux/app"),
        "PYTHONPATH": str(ROOT / "dist/WiiM-Home-Linux/app"),
    },
    capture_output=True,
    text=True,
    check=False,
)
lock.close()
assert result.returncode == 2, result.returncode
assert bootstrap_result.returncode == 2, bootstrap_result.returncode
assert "already running" in bootstrap_result.stderr

import socket
from single_instance import reserve_observer_port, take_observer_reservation

with socket.socket() as probe:
    probe.bind(("127.0.0.1", 0))
    observer_port = probe.getsockname()[1]
listener = reserve_observer_port(observer_port)
assert listener.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR) == 1
assert not hasattr(socket, "SO_REUSEPORT") or listener.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT) == 0
take_observer_reservation(observer_port).close()
print("single instance guard: PASS")
