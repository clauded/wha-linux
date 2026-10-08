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
This has only been tested on Arch Linux.

The script extracts the application locally, creates a Linux Python/Qt runtime and applies a small set of Linux compatibility fixes so that the WiiM Home desktop application can run natively on Linux.

To build the Linux executable on Arch, you need :
- python python-requests 
- uv
- 7zip
- qt6-base
- wireless tools
- gst-plugins-good
- gst-plugins-bad
- gst-plugins-ugly

You will also need to download the official Wiim for Mac image available on the Wiim web site (https://www.wiimhome.com/app). Tested with version 0.2.10.4.

Building
--------
To build with Python :
`sh wha-linux.sh /path/to/official-x86_64.dmg`

This will create a run.sh script located in a subdirectory of **$HOME/.local/share/wha-linux**

Running
-------
You can call the script with the **wiim** bash script. Simply copy the file to your local bin directory ($HOME/bin) and make it executable. If you want to add a launcher, you can use the .desktop file but you'll need to edit it to point the the directory where **run.sh** is created.

Known bugs
----------
- Presets are not available.

Credits
-------
Author : *Malfman* (see https://forum.wiimhome.com/threads/native-wiim-home-on-linux-%E2%80%93-the-desktop-app-is-basically-python-qt.10413/)
