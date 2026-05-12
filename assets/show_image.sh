#!/usr/bin/env bash
set -euo pipefail

# Default image: same directory/goobo_startup_480x640.png
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_PATH="${1:-${SCRIPT_DIR}/goobo_startup_480x640.png}"

if [[ "${EUID}" -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

if [[ ! -f "${IMAGE_PATH}" ]]; then
    echo "ERROR: image not found:"
    echo "  ${IMAGE_PATH}"
    exit 1
fi

echo "[INFO] Stop old fbi process..."
killall fbi 2>/dev/null || true

echo "[INFO] Stop desktop login screen and tty1 login prompt..."
systemctl stop display-manager.service 2>/dev/null || true
systemctl stop getty@tty1.service 2>/dev/null || true

echo "[INFO] Switch to tty1..."
chvt 1 || true

echo "[INFO] Unblank framebuffer..."
if [[ -e /sys/class/graphics/fb0/blank ]]; then
    echo 0 > /sys/class/graphics/fb0/blank || true
fi

echo "[INFO] Disable terminal blanking and cursor..."
sh -c 'TERM=linux setterm -blank 0 -powerdown 0 -cursor off < /dev/tty1 > /dev/tty1' || true

echo "[INFO] Set backlight to max..."
for b in /sys/class/backlight/*; do
    [[ -d "$b" ]] || continue
    max="$(cat "$b/max_brightness" 2>/dev/null || echo 255)"
    echo "$max" > "$b/brightness" 2>/dev/null || true
done

echo "[INFO] Show image on /dev/fb0:"
echo "  ${IMAGE_PATH}"

fbi -T 1 -d /dev/fb0 -a --noverbose "${IMAGE_PATH}"
