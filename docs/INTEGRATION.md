# Integration package for clauded/wha-linux

This package updates the builder; it does not contain WiiM application files.
The original official DMG is still required. No installer, extracted bytecode,
QML, icons, binaries, user/account data, cache or runtime logs are redistributed.

## Apply to Claude's main branch

Target baseline: `178ee738a246e0a7cfc1e7ea91e5915edce5b967` from
https://github.com/clauded/wha-linux (also Samuel-Boehm's main baseline).
The script does not reset, commit, push, install system packages or start an app.
It checks its checksums and `git apply --check` before applying anything.

```sh
tar xf claude-wha-linux-compat-20261101.tar.gz
cd claude-wha-linux-compat-20261101
./apply.sh /path/to/your/wha-linux-checkout
```

Alternatively, in the target checkout:

```sh
git apply --check /path/to/integration.patch
git apply /path/to/integration.patch
```

If the patch conflicts, stop and review; do not force it or overwrite a newer
checkout. The package targets main, not a feature branch already containing a
different `wha-linux.sh`. The legacy versioned scripts/assets remain untouched.

## Try without applying the patch

The package also includes the fully readable standalone `wha-linux.sh`:

```sh
sh wha-linux.sh "/path/to/WiiM Home Setup-x86_64.dmg" --build-only
sh wha-linux.sh "/path/to/WiiM Home Setup-x86_64.dmg"
```

Download the current macOS x86_64 installer yourself from https://wiimhome.com/app.
Current official x86_64 version checked on 2026-11-01: **0.2.11.7**.
Do not use mirrors or send us an installer/account cache.

For future installer hashes add `--allow-untested`. It remains experimental:
the Python, binding/profile, resource and patch checks must still pass.
Use `--debug` for detailed diagnostics and `--hide-to-tray` to opt into hiding
on X. Normal runs are quiet and X quits by default.

## Maintenance and validation

The package adds modular, authored sources under `buildkit/`. Do not manually
edit the generated script; regenerate it with:

```sh
python3 tools/package_wrapper.py
python3 tests/test_build_compatibility.py
sh wha-linux.sh /path/to/official.dmg --build-only
python3 tools/verify_build.py /printed/path/out/WiiM-Home-Linux
python3 tests/native_lifecycle.py /printed/path/out/WiiM-Home-Linux
```

See `docs/COMPATIBILITY.md` and the included `TEST_RESULTS.json` for exact
versions, hashes, covered behavior and limitations. Both 0.2.10.5 and 0.2.11.7
were clean-built and passed 14 device-free regressions plus actual native
offscreen start/close/restart tests. 0.2.10.4 is a historical reference, not a
freshly tested input. Physical devices, streaming accounts, OAuth and interactive
GNOME/Plasma appearance were not retested for this update. Some shutdowns still
use the ORIGINAL application's watchdog; no new forced-kill hook was introduced.

The useful flexibility ideas from Samuel-Boehm (explicit untested mode,
0.2.10.5 recognition, cross-desktop/distribution considerations) are retained.
This is a targeted integration, not a blind merge of forced KDE/X11 behavior or
aggressive shutdown patches. Existing Linux TIDAL/cache/Preset/USB/observer fixes
are preserved and tested.
