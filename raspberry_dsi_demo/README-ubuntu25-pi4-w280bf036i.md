# W280BF036I DSI Display on Raspberry Pi 4 Ubuntu 25.x

This patch makes the W280BF036I Raspberry Pi DSI display driver work on Ubuntu 25.x Raspberry Pi kernel.

## Tested environment

- Board: Raspberry Pi 4
- OS: Ubuntu 25.x for Raspberry Pi
- Kernel example: `6.17.0-1011-raspi`
- Display: W280BF036I DSI panel
- Boot firmware directory layout:
  - Config: `/boot/firmware/config.txt`
  - Overlays: `/boot/firmware/current/overlays`

## Problem

The original driver/installer assumes a Raspberry Pi OS / Debian-style layout and may install overlays to the wrong path.

On Ubuntu 25.x, the correct overlay directory can be:

```bash
/boot/firmware/current/overlays