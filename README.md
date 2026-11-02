# wha-linux
**Run Wiim Home on Linux**

This is not a clean-room reimplementation of WiiM Home. It reuses the platform-independent code and resources from the official installers and replaces the macOS/Windows runtime parts with Linux-native equivalents.

There are a few Linux-specific issues, but they are relatively small. The striking part is that WiiM apparently already did most of the work required for a Linux version simply by choosing Python + Qt/QML for the desktop client.

This is an unofficial community experiment and obviously not supported by WiiM. Nothing is uploaded anywhere: usage of the official DMG happens locally on the user's machine.

History
-------
A large part of the actual WiiM logic is Python bytecode, while much of the user interface is normal QML. The application also contains the device discovery/networking code and the desktop implementations for services such as TIDAL and Qobuz.

So instead of trying to emulate the Windows version with Wine or running the Android version in Waydroid, Codex was asked it to construct a small application glue with a native Linux Python/Qt runtime using the official macOS DMG and Windows. The file **wiim-prompt.txt** contains the instructions used for Codex.

Requirement
-----------
Tested on Arch Linux (KDE Plasma) and Fedora 44 (GNOME).

The script extracts the application locally, creates a Linux Python/Qt runtime and applies a small set of Linux compatibility fixes so that the WiiM Home desktop application can run natively on Linux.

To build the Linux executable on Arch, you need :
- python python-requests 
- uv
- 7zip
- qt6-base
- gst-plugins-good
- gst-plugins-bad
- gst-plugins-ugly
- wireless tools

`pacman -S python python-requests uv 7zip qt6-base gst-plugins-good gst-plugins-bad gst-plugins-ugly wireless tools`

On Fedora, you need:
- python3 python3-requests
- uv
- 7zip
- qt6-qtbase-devel
- gstreamer1-plugins-good
- gstreamer1-plugins-bad-free
- gstreamer1-plugins-ugly-free

`sudo dnf install python3 python3-requests uv 7zip qt6-qtbase-devel gstreamer1-plugins-good gstreamer1-plugins-bad-free gstreamer1-plugins-ugly-free`

You will also need to download the official Wiim for Mac image available on the Wiim web site (https://www.wiimhome.com/app). Tested up to version 0.2.11.7.

Building
--------
To build with Python :
`sh wha-linux.sh "/path/to/WiiM Home Setup-x86_64.dmg"`

This will create a run.sh script located in a subdirectory of **$HOME/.local/share/wha-linux**.
After building, the script starts WiiM Home right away. On this first start the app adds itself to your desktop's application menu.

WiiM Home **0.2.11.7** is the current official macOS x86_64 download checked on 2026-11-01. 
For later official installers use `--allow-untested` explicitly. 
This does not disable bytecode, Qt-profile, resource, or guarded patch checks. 

Python and Qt debug/info output is off by default; use `--debug` for troubleshooting. 
X quits by default; `--hide-to-tray` opts into the original tray behavior for that run.

See [docs/COMPATIBILITY.md](docs/COMPATIBILITY.md) for the test matrix and limits. 
Maintainers edit `buildkit/` and run `python3 tools/package_wrapper.py`, rather than hand-editing the embedded standalone script.

Running
-------
You start the application from the startup menu or can call it from terminal with the **wiim** bash script. Simply copy the **wiim** file to your local bin directory ($HOME/bin) and make it executable. 

Known bugs
----------
- Presets are not available.
- Only the music services built into the official desktop app are available and local/media-server music. Services such as YouTube Music, Spotify or Amazon Music exist only in the mobile apps.

Credits
-------
- Author : *Malfman* (see https://forum.wiimhome.com/threads/native-wiim-home-on-linux-%E2%80%93-the-desktop-app-is-basically-python-qt.10413/)
- Contributor(s): *clauded*, *Samuel-Boehm* (0.2.10.5, guarded untested-source workflow and desktop portability)

