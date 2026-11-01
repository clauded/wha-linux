"""Quiet production logging, with explicit diagnostics for this launch only."""
import argparse
import logging
import os
import sys


def configure_runtime_options():
    parser = argparse.ArgumentParser(description="Native WiiM Home")
    parser.add_argument("--debug", action="store_true", default=os.environ.get("WIIM_DEBUG") == "1")
    parser.add_argument("--hide-to-tray", action="store_true", default=os.environ.get("WIIM_HIDE_TO_TRAY") == "1")
    options, remaining = parser.parse_known_args()
    sys.argv[1:] = remaining
    os.environ["WIIM_HIDE_TO_TRAY"] = "1" if options.hide_to_tray else "0"
    # Upstream configures its own loggers at import time. A global threshold
    # also applies to those loggers without changing their handlers or format.
    logging.disable(logging.NOTSET if options.debug else logging.INFO)
    if not options.debug:
        from qt_compat.QtCore import QtMsgType, qFormatLogMessage, qInstallMessageHandler

        def qt_message(kind, context, message):
            if kind in (QtMsgType.QtDebugMsg, QtMsgType.QtInfoMsg):
                return
            if previous is not None:
                previous(kind, context, message)
            else:
                print(qFormatLogMessage(kind, context, message), file=sys.stderr, flush=True)

        previous = qInstallMessageHandler(qt_message)
    return options
