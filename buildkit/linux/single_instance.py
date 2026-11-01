"""Linux process guard for WiiM Home's fixed local listener set."""
import errno
import os
import socket


_observer_reservation = None


class AlreadyRunning(RuntimeError):
    pass


class ObserverPortUnavailable(RuntimeError):
    pass


def acquire():
    """Hold an advisory lock until process exit; stale files do not block restart."""
    import fcntl

    directory = os.environ.get("XDG_RUNTIME_DIR") or os.environ.get("XDG_CACHE_HOME")
    if not directory:
        directory = os.path.join(os.environ.get("WIIM_HOME_APP", "."), "cache")
    os.makedirs(directory, exist_ok=True)
    path = os.path.join(directory, "wiim-home-linux.lock")
    handle = open(path, "a+", encoding="utf-8")
    try:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as error:
        if error.errno not in (errno.EACCES, errno.EAGAIN):
            raise
        handle.seek(0)
        owner = handle.read().strip() or "unknown"
        handle.close()
        raise AlreadyRunning("WiiM Home is already running (lock owner PID %s)" % owner)
    handle.seek(0)
    handle.truncate()
    handle.write(str(os.getpid()))
    handle.flush()
    return handle


def install_signal_cleanup():
    """Let SIGTERM/SIGINT travel through Qt's normal close lifecycle."""
    import signal

    def request_quit(signum, _frame):
        from qt_compat.QtWidgets import QApplication

        app = QApplication.instance()
        if app is None:
            raise SystemExit(128 + signum)
        app.quit()

    signal.signal(signal.SIGTERM, request_quit)
    signal.signal(signal.SIGINT, request_quit)


def reserve_observer_port(port=22334):
    """Reserve the fixed callback port and permit an immediate clean restart."""
    global _observer_reservation
    if _observer_reservation is not None:
        return _observer_reservation
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        listener.bind(("0.0.0.0", port))
        listener.listen(5)
    except OSError as error:
        listener.close()
        if error.errno == errno.EADDRINUSE:
            raise ObserverPortUnavailable(
                "UPnP observer port %d is already in use; quit the process owning it before starting WiiM Home" % port
            )
        raise
    _observer_reservation = listener
    return listener


def take_observer_reservation(port):
    global _observer_reservation
    listener = _observer_reservation
    if listener is None or listener.getsockname()[1] != port:
        return None
    _observer_reservation = None
    return listener
