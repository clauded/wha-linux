# wha-linux
Run Wiim Home on Linux

This is not a clean-room reimplementation of WiiM Home. It reuses the platform-independent code and resources from the official installers and replaces the macOS/Windows runtime parts with Linux-native equivalents.

There were a few Linux-specific issues, but they were relatively small. The striking part is that WiiM apparently already did most of the work required for a Linux version simply by choosing Python + Qt/QML for the desktop client.

Requirement
-----------
This has only been tested on Arch Linux.

The script extracts the application locally, creates a Linux Python/Qt runtime and applies a small set of Linux compatibility fixes so that the WiiM Home desktop application can run natively on Linux.

To build the Linux executable you need :
-python
-uv
-7zip
-qt6-base
-wireless tools

You will also need to download the official Wiim for Mac image available on the Wiim web site (https://www.wiimhome.com/app). Tested with version 0.2.10.4.

Building
--------

Run:
  sh wha-linux.sh /path/to/official-x86_64.dmg 

This will create a run.sh script located in a subdirectory of $HOME/.local/share/wha-linux

Running
-------
