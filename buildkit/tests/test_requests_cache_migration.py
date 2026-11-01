#!/usr/bin/env python3
"""Only disposable HTTP cache rows are invalidated on a cache-runtime change."""
import json
import sqlite3
import tempfile
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "linux"))
from cache_compat import ensure_http_cache_compatibility

with tempfile.TemporaryDirectory() as directory:
    root = Path(directory)
    database_path = root / "tidal_request_cache.sqlite"
    with sqlite3.connect(database_path) as database:
        database.execute("CREATE TABLE responses (key TEXT PRIMARY KEY, value BLOB, expires INTEGER)")
        database.execute("CREATE TABLE redirects (key TEXT PRIMARY KEY, value BLOB, expires INTEGER)")
        database.execute("INSERT INTO responses VALUES ('legacy', X'00', NULL)")
    (root / "deviceCacheV2.json").write_text('{"device": true}', encoding="utf-8")
    (root / "requests-cache-runtime.json").write_text(json.dumps({"requests_cache": "1.3.3", "datetime_mode": "aware-utc"}), encoding="utf-8")

    backups = ensure_http_cache_compatibility(root)
    assert len(backups) == 1 and Path(backups[0]).exists()
    with sqlite3.connect(database_path) as database:
        assert database.execute("SELECT count(*) FROM responses").fetchone()[0] == 0
    assert (root / "deviceCacheV2.json").read_text(encoding="utf-8") == '{"device": true}'
    assert json.loads((root / "requests-cache-runtime.json").read_text())['requests_cache'] == '1.0.1'

    with sqlite3.connect(database_path) as database:
        database.execute("INSERT INTO responses VALUES ('current', X'00', NULL)")
    assert ensure_http_cache_compatibility(root) == []
    with sqlite3.connect(database_path) as database:
        assert database.execute("SELECT count(*) FROM responses").fetchone()[0] == 1
print("requests-cache migration: PASS")
