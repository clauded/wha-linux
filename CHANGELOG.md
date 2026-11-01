2026-11-01 — current installer compatibility integration
-------------------------------------------------------
- Add version-independent readable wha-linux.sh and its modular buildkit.
- Validate native builds of 0.2.10.5 (PyQt6) and 0.2.11.7 (PySide6 6.8.3).
- Detect the typed PYZ entry, verify Python magic, detect active Qt imports.
- Materialize embedded QML before guarded semantic edits; rebuild/verify qrc.
- Allow explicit untested sources without disabling structural patch checks.
- Preserve quiet/debug and quit/tray options, existing Linux compatibility fixes.
- Include device-free regressions and isolated native lifecycle tests.
- No proprietary installer/application payload is included.

Changelog
---------

2024-10-07
----------
wha-linux-0.2.10.4.sh : 

- allow to disable debug messages
- quit python when gui is closed
- version with Plasma decoration to match kde desktop
- .desktop file and launcher

The original script from Malfman is wha-linux-0.2.10.4.sh.orig.
