#!/usr/bin/env bash
set -euo pipefail

# Ubuntu 25.x + Raspberry Pi 4 + W280BF036I DSI display installer
# Fixes:
# 1. Ubuntu Raspberry Pi overlay path: /boot/firmware/current/overlays
# 2. Duplicate backlight issue: gpio-backlight vs driver-created DCS backlight
# 3. Avoid using upstream make install because it assumes Raspberry Pi OS/Debian-style paths

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
SRC_DIR="$REPO_DIR/raspberry_dsi_demo/src"

DTS_FILE="$SRC_DIR/dts/vc4-kms-dsi-w280bf036i-pi4.dts"
DTBO_FILE="$SRC_DIR/vc4-kms-dsi-rpidisp.dtbo"
KO_FILE="$SRC_DIR/panel-rpi-dsi-display.ko"

BOOT_FW="/boot/firmware"
OVERLAY_DIR="$BOOT_FW/current/overlays"
CONFIG_FILE="$BOOT_FW/config.txt"

MODULE_DEST="/lib/modules/$(uname -r)/kernel/drivers/gpu/drm/panel"

echo "[INFO] Repo dir: $REPO_DIR"
echo "[INFO] Kernel: $(uname -r)"

if [[ ! -d "$SRC_DIR" ]]; then
    echo "[ERROR] src directory not found: $SRC_DIR"
    exit 1
fi

if [[ ! -f "$DTS_FILE" ]]; then
    echo "[ERROR] DTS file not found: $DTS_FILE"
    exit 1
fi

echo "[STEP 1] Installing build dependencies..."
sudo apt update
sudo apt install -y \
    build-essential \
    dkms \
    flex \
    bison \
    bc \
    libssl-dev \
    libelf-dev \
    device-tree-compiler \
    linux-headers-"$(uname -r)"

echo "[STEP 2] Checking Ubuntu Raspberry Pi boot overlay path..."
if [[ ! -d "$OVERLAY_DIR" ]]; then
    echo "[ERROR] Overlay directory not found: $OVERLAY_DIR"
    echo "[INFO] Current detected overlay directories:"
    sudo find /boot -maxdepth 4 -type d -name overlays -print || true
    exit 1
fi

# Some wrong install scripts may create /boot/firmware/overlays as a regular file.
if [[ -f "$BOOT_FW/overlays" && ! -d "$BOOT_FW/overlays" ]]; then
    echo "[WARN] $BOOT_FW/overlays is a regular file, renaming it."
    sudo mv "$BOOT_FW/overlays" "$BOOT_FW/overlays.bad.$(date +%Y%m%d-%H%M%S)"
fi

echo "[STEP 3] Patching DTS to remove duplicate gpio-backlight node..."
cp "$DTS_FILE" "$DTS_FILE.bak.$(date +%Y%m%d-%H%M%S)"

python3 - <<PY
from pathlib import Path

p = Path("$DTS_FILE")
text = p.read_text()
lines = text.splitlines(keepends=True)

out = []
i = 0
removed_node = False
commented_backlight = False

while i < len(lines):
    line = lines[i]

    # Remove the whole node:
    # rpi_dsi_display_bl:rpi-dsi-display-bl { ... };
    if "rpi_dsi_display_bl" in line and "rpi-dsi-display-bl" in line and "{" in line:
        removed_node = True

        brace = line.count("{") - line.count("}")
        i += 1
        while i < len(lines):
            brace += lines[i].count("{") - lines[i].count("}")
            if brace <= 0 and "};" in lines[i]:
                i += 1
                break
            i += 1
        continue

    # Comment out:
    # backlight = <&rpi_dsi_display_bl>;
    if "backlight" in line and "rpi_dsi_display_bl" in line and not line.lstrip().startswith("//"):
        out.append("// " + line)
        commented_backlight = True
        i += 1
        continue

    out.append(line)
    i += 1

p.write_text("".join(out))

print(f"[PATCH] removed gpio-backlight node: {removed_node}")
print(f"[PATCH] commented panel backlight reference: {commented_backlight}")
PY

echo "[STEP 4] Building kernel module and overlay..."
cd "$SRC_DIR"
make clean
make w280bf036i

if [[ ! -f "$DTBO_FILE" ]]; then
    echo "[ERROR] DTBO not generated: $DTBO_FILE"
    exit 1
fi

if [[ ! -f "$KO_FILE" ]]; then
    echo "[ERROR] Kernel module not generated: $KO_FILE"
    exit 1
fi

echo "[STEP 5] Verifying patched DTBO..."
dtc -I dtb -O dts "$DTBO_FILE" -o /tmp/vc4-kms-dsi-rpidisp-patched.dts 2>/dev/null || true

if grep -qE "rpi-dsi-display-bl|gpio-backlight|backlight = <&rpi_dsi_display_bl>" /tmp/vc4-kms-dsi-rpidisp-patched.dts; then
    echo "[ERROR] Patched DTBO still contains gpio-backlight/backlight reference."
    echo "[INFO] Matched lines:"
    grep -nE "rpi-dsi-display-bl|gpio-backlight|backlight" /tmp/vc4-kms-dsi-rpidisp-patched.dts || true
    exit 1
else
    echo "[OK] DTBO no longer contains duplicate gpio-backlight node."
fi

echo "[STEP 6] Installing DTBO and kernel module manually..."
sudo cp "$DTBO_FILE" "$OVERLAY_DIR/"
sudo mkdir -p "$MODULE_DEST"
sudo cp "$KO_FILE" "$MODULE_DEST/"
sudo depmod -a

echo "[STEP 7] Patching /boot/firmware/config.txt..."
sudo cp "$CONFIG_FILE" "$CONFIG_FILE.bak.$(date +%Y%m%d-%H%M%S)"

# Fix accidental .[all] typo if present.
sudo sed -i 's/^\.\[all\]/[all]/' "$CONFIG_FILE"

# Comment old conflicting lines.
sudo sed -i \
    -e 's/^[[:space:]]*dtoverlay=vc4-kms-v3d.*/# &/' \
    -e 's/^[[:space:]]*dtoverlay=vc4-kms-dsi-rpidisp.*/# &/' \
    -e 's/^[[:space:]]*dtoverlay=vc4-kms-dsi-w280bf036i-touch.*/# &/' \
    -e 's/^[[:space:]]*display_auto_detect=.*/# &/' \
    -e 's/^[[:space:]]*ignore_lcd=.*/# &/' \
    "$CONFIG_FILE"

# Remove old managed block if it exists.
sudo sed -i '/# BEGIN W280BF036I UBUNTU25 FIX/,/# END W280BF036I UBUNTU25 FIX/d' "$CONFIG_FILE"

sudo tee -a "$CONFIG_FILE" >/dev/null <<'EOF'

# BEGIN W280BF036I UBUNTU25 FIX
[all]
dtoverlay=vc4-kms-v3d,cma-128
disable_fw_kms_setup=1
display_auto_detect=0
dtoverlay=vc4-kms-dsi-rpidisp
dtparam=i2c_vc=on
# Touch overlay is intentionally disabled first.
# dtoverlay=vc4-kms-dsi-w280bf036i-touch
# END W280BF036I UBUNTU25 FIX
EOF

echo "[STEP 8] Final checks..."
echo "[INFO] Installed overlay:"
ls -l "$OVERLAY_DIR/vc4-kms-dsi-rpidisp.dtbo"

echo "[INFO] Installed module:"
modinfo panel-rpi-dsi-display | head -20 || true

echo
echo "[OK] Installation finished."
echo "[NEXT] Reboot now:"
echo "      sudo reboot"
echo
echo "[AFTER REBOOT] Check:"
echo "      ls /sys/class/drm"
echo "      ls /sys/class/backlight"
echo "      sudo dmesg | grep -iE 'rpi_dsi|rpi-dsi|dsi|panel|backlight|drm|vc4|probe|fail|error'"
