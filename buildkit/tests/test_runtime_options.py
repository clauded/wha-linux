"""Check real Python/Qt output filtering in separate processes."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
program = '''
import logging, os, sys
sys.path.insert(0, sys.argv.pop(1))
from runtime_options import configure_runtime_options
options = configure_runtime_options()
logging.basicConfig(level=logging.DEBUG)
logging.debug("PY_DEBUG_TEST")
logging.info("PY_INFO_TEST")
logging.warning("PY_WARNING_TEST")
logging.error("PY_ERROR_TEST")
from qt_compat.QtCore import qDebug, qInfo, qWarning, qCritical
qDebug("QT_DEBUG_TEST")
qInfo("QT_INFO_TEST")
qWarning("QT_WARNING_TEST")
qCritical("QT_CRITICAL_TEST")
print("HIDE=" + os.environ["WIIM_HIDE_TO_TRAY"])
print("REMAINING=" + repr(sys.argv[1:]))
'''
for flags, env_debug, debug in (([], "0", False), (["--debug", "--hide-to-tray"], "0", True), ([], "1", True)):
    result = subprocess.run([sys.executable, "-c", program, str(ROOT / "linux")] + flags,
                            env=dict(os.environ, WIIM_DEBUG=env_debug, WIIM_HIDE_TO_TRAY="0"),
                            text=True, capture_output=True, check=False, cwd=ROOT)
    assert result.returncode == 0, result.stdout + result.stderr
    for name in ("PY_DEBUG_TEST", "PY_INFO_TEST", "QT_DEBUG_TEST", "QT_INFO_TEST"):
        assert (name in result.stderr) == debug, (name, result.stderr)
    for name in ("PY_WARNING_TEST", "PY_ERROR_TEST", "QT_WARNING_TEST", "QT_CRITICAL_TEST"):
        assert name in result.stderr, (name, result.stderr)
    assert "HIDE=" + ("1" if "--hide-to-tray" in flags else "0") in result.stdout
    assert "REMAINING=[]" in result.stdout
print("Quiet Python/Qt output; warnings/errors retained; explicit debug: PASS")
