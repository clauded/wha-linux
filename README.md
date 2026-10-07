# wha-linux
Run Wiim Home on Linux

This is not a clean-room reimplementation of WiiM Home. It reuses the platform-independent code and resources from the official installers and replaces the macOS/Windows runtime parts with Linux-native equivalents.

There were a few Linux-specific issues, but they were relatively small. The striking part is that WiiM apparently already did most of the work required for a Linux version simply by choosing Python + Qt/QML for the desktop client.

