#!/usr/bin/env python3
"""Ensure the original WiiM URL-cache API remains available and semantically usable."""
import tempfile

import requests_cache

assert requests_cache.__version__ == "1.0.1", requests_cache.__version__
with tempfile.TemporaryDirectory() as directory:
    session = requests_cache.CachedSession(cache_name=directory + "/radio-paradise", backend="sqlite")
    url = "https://api.radioparadise.com/api/1/profile"
    assert session.cache.has_url(url) is False
    assert session.cache.has_url(url, method="POST") is False
    session.cache.close()
print("requests-cache legacy URL API: PASS")
