"""Version-gate disposable requests-cache databases without touching user state."""
import json
import shutil
import sqlite3
from datetime import datetime
from pathlib import Path


_DATABASES = ("tidal_request_cache.sqlite", "request_cache.sqlite", "wiimradio_api_cache.sqlite")
_MARKER = "requests-cache-runtime.json"
_DATETIME_MODE = "naive-utc"


def _runtime_marker():
    import requests_cache

    return {"requests_cache": requests_cache.__version__, "datetime_mode": _DATETIME_MODE}


def _response_count(path):
    with sqlite3.connect(path) as database:
        table = database.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='responses'").fetchone()
        return database.execute("SELECT count(*) FROM responses").fetchone()[0] if table else 0


def _clear_database(path, backup_dir):
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / (path.stem + ".pre-cache-migration-" + datetime.utcnow().strftime("%Y%m%dT%H%M%SZ") + path.suffix)
    shutil.copy2(path, backup)
    with sqlite3.connect(path) as database:
        database.execute("DELETE FROM responses")
        table = database.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='redirects'").fetchone()
        if table:
            database.execute("DELETE FROM redirects")
        database.commit()
    return backup


def ensure_http_cache_compatibility(cache_root):
    """Invalidate only HTTP response caches when their runtime marker changes."""
    cache_root = Path(cache_root)
    cache_root.mkdir(parents=True, exist_ok=True)
    marker_path = cache_root / _MARKER
    expected = _runtime_marker()
    try:
        observed = json.loads(marker_path.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError, OSError):
        observed = None

    invalidated = []
    if observed != expected:
        backup_dir = cache_root / "requests-cache-backups"
        for name in _DATABASES:
            path = cache_root / name
            if path.exists() and _response_count(path):
                invalidated.append(str(_clear_database(path, backup_dir)))
    marker_path.write_text(json.dumps(expected, sort_keys=True) + "\n", encoding="utf-8")
    return invalidated
