#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: run this installer with sudo."
    echo "Example: sudo ./install_environment.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"

echo "Goobo project directory: ${SCRIPT_DIR}"
echo "Target non-root user: ${TARGET_USER}"

echo "Updating apt package index..."
apt update

echo "Installing Goobo system dependencies..."
apt-get install -y \
    sudo \
    git \
    openssl \
    build-essential \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-cffi \
    python3-numpy \
    python3-pycparser \
    python3-serial \
    python3-rpi-lgpio \
    python3-rpi-ws281x \
    rpicam-apps \
    libcamera-tools \
    ffmpeg \
    v4l-utils \
    pulseaudio \
    pulseaudio-utils \
    libpulse-dev \
    alsa-utils \
    libportaudio2 \
    portaudio19-dev

echo "Installing Goobo Python audio dependency..."
python3 -m pip install --break-system-packages --resume-retries 10 --timeout 120 sounddevice

HARDWARE_GROUPS=(dialout video audio render gpio i2c spi)

echo "Adding ${TARGET_USER} to hardware access groups..."
for group in "${HARDWARE_GROUPS[@]}"; do
    if getent group "${group}" >/dev/null; then
        usermod -aG "${group}" "${TARGET_USER}"
        echo "Added ${TARGET_USER} to ${group}"
    else
        echo "Group ${group} does not exist, skipped."
    fi
done

echo "Checking optional Raspberry Pi DSI display installer..."

DSI_DIR="${SCRIPT_DIR}/raspberry_dsi_demo"
DSI_INSTALLER="${DSI_DIR}/install_ubuntu25_pi4_w280.sh"

if [[ -f "${DSI_INSTALLER}" ]]; then
    echo "Found DSI installer: ${DSI_INSTALLER}"

    echo "Fixing ownership of raspberry_dsi_demo for ${TARGET_USER}..."
    chown -R "${TARGET_USER}:${TARGET_USER}" "${DSI_DIR}"

    echo "Making DSI installer executable..."
    chmod +x "${DSI_INSTALLER}"

    echo "Installing W280BF036I DSI display driver as ${TARGET_USER}..."
    sudo -u "${TARGET_USER}" -H bash "${DSI_INSTALLER}"

    echo "DSI display driver installation finished."
else
    echo "DSI installer not found, skipped:"
    echo "  ${DSI_INSTALLER}"
fi

echo
echo "Goobo environment installation finished."
echo "Please reboot before using hardware tools without sudo:"
echo "  sudo reboot"