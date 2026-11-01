# Installer compatibility and integration notes

## What changed

The official macOS x86_64 installer downloaded from
https://wiimhome.com/app on 2026-11-01 is **0.2.11.7**, build
`20261027115101`, SHA-256
`24a1ae3b96d5f97e7fe36a5e1b9cd26847b21ae51d8c4b51f2cd6268605174ca`.
No newer x86_64 build was offered by that official download endpoint at this check.
The user's "2.11.7" is the desktop application's full version **0.2.11.7**.

| Input | PYZ entry | Native Linux Qt profile | QML input | Current validation |
| --- | --- | --- | --- | --- |
| 0.2.10.4 | legacy PYZ | PyQt6 6.10.2 | loose + embedded | historical local release; original DMG no longer available here |
| 0.2.10.5 | PYZ-00.pyz | PyQt6 6.10.2 | loose + embedded | clean standalone build, 14 regressions, native lifecycle |
| 0.2.11.7 | PYZ.pyz | PySide6 6.8.3 | embedded-only | clean standalone build, 14 regressions, native lifecycle |

The old installer currently present here is actually 0.2.10.5, SHA-256
`ae73625fab54d60b87f69aa427d04044e43b6ec5ba7f91269d00c1dcd56022eb`.
This independently validates the old-layout input reported by Samuel-Boehm.

The breakage is not just a source hash change. Hardcoding `PYZ-00.pyz`, installing
only PyQt6, and blindly copying a nonexistent `Resources/Qml` all fail for the
new official distribution. The new reader finds the archive by its CArchive
type, checks magic `610d0d0a`, and reads the application's actual Qt imports.
Own adapters/tests use a small binding-neutral import helper; proprietary
application code imports its original binding unchanged. There is no global
PySide/PyQt monkey-patch or bytecode translation.

## Controlled flexibility

- `--allow-untested` (alias `--force-untested-source`) permits a different
  locally downloaded installer hash. Unknown inputs are not called verified.
- Python bytecode must match the pinned CPython 3.9.25 runtime. A different
  Python bytecode generation stops before unmarshalling/execution.
- Active PyQt6 and the PySide6 6.8 series have explicit pinned Linux profiles.
  A different Qt binding or unsupported PySide series requires review.
- PYZ filename changes, volume/folder names, and loose-versus-embedded QML
  do not require a new hardcoded installer layout.
- QML edits identify individual functions and compare hashes of executable
  tokens, ignoring comments/whitespace. Different application logic fails closed.
  Already-applied replacements are accepted. All edit preconditions are checked
  before writes; no generic search-and-replace or broad exception suppression.
- The actual compiled qrc is rebuilt and checked, not just the loose QML tree.
- RCC lookup handles common Arch/Fedora/Debian paths and requires Qt 6.
- Source and wrapper SHA-256 values select separate build directories. No
  existing runtime/config/account data is overwritten by building a new version.

This is guarded extensibility, not a promise that every future installer works.
Novel Python/Qt APIs, moved entry points, or changed target functions need review.
Only official installers supplied by the user are supported; unknown-hash mode
does not establish provenance. Review/download from the official site first.

## Reproducing tests

Manjaro Linux, x86_64, kernel `6.12.108-1-MANJARO`. Arch prerequisites:

```sh
sudo pacman -S python uv 7zip qt6-base
```

Fedora prerequisite guidance (not a Fedora execution claim):

```sh
sudo dnf install python3 uv 7zip qt6-qtbase-devel
```

```sh
python3 tools/package_wrapper.py
python3 tests/test_build_compatibility.py
sh wha-linux.sh /path/to/official.dmg --build-only
python3 tools/verify_build.py /printed/path/out/WiiM-Home-Linux
python3 tests/native_lifecycle.py /printed/path/out/WiiM-Home-Linux
```

`verify_build.py` copies only authored tests/adapters to a temporary test harness,
uses the actual built application/resources, and isolates all test state. The
14 existing tests cover TIDAL Home and asynchronous Collection (empty to
35/10/10/49; Tracks 49 to 7 to 0 to 12), cache API/migration, Radio Paradise,
Preset parsing/callback, USB output, radio artwork, icons, single instance,
observer lifecycle, close callbacks, and quiet/debug logging.

`native_lifecycle.py` uses a private network namespace, offscreen Qt, isolated
XDG state, and the actual application's X callbacks: quit; hide/restore/quit;
restart/quit; quiet/quit. It checks the main window and rebinds all four local
listener ports after each exit. Linux unshare/ip support is needed for this
optional test. It never controls LAN devices or uses real accounts.

## Preserved fixes / limits

TIDAL loading and reactive Collection counts, real qrc propagation, cache 1.0.1
migration, Radio Paradise cache APIs, Presets, USB normalization, observer
reservation/lifecycle and single-instance protection, radio artwork, and desktop
identity remain included. Diagnostics remain quiet by default. No forced global
KDE theme, mandatory X11 backend, or new aggressive kill hook was introduced.

Some exits still use the ORIGINAL WiiM 500ms watchdog (SIGKILL); this is not a
claim of fully graceful shutdown. No real-device playback, account/OAuth flow,
interactive GNOME/Plasma/Wayland appearance, or real system-tray clicking was
retested for this update. Complete real-device acceptance before release.

Only authored tooling, hash-based transformations, tests, pinned dependencies,
and documentation are distributable. Do not commit/ship rebuilt clients, QML,
icons, bytecode, installers, tokens, logs, config, or caches.
