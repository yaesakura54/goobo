#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: run this installer with sudo."
    echo "Example: sudo ./scripts/install_environment.sh"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
TARGET_USER="${SUDO_USER:-$USER}"

echo "Goobo project directory: ${REPO_DIR}"
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
    portaudio19-dev \
    fbset \
    fbi \
    imagemagick

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

DSI_DIR="${REPO_DIR}/raspberry_dsi_demo"
DSI_INSTALLER="${REPO_DIR}/scripts/raspberry_dsi/install_ubuntu25_pi4_w280.sh"

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

echo "Preparing Goobo framebuffer image display tools..."

ASSETS_DIR="${REPO_DIR}/assets"
DISPLAY_SCRIPT="${REPO_DIR}/scripts/display/show_image.py"

if [[ -d "${ASSETS_DIR}" ]]; then
    chown -R "${TARGET_USER}:${TARGET_USER}" "${ASSETS_DIR}"

    if [[ -f "${DISPLAY_SCRIPT}" ]]; then
        chmod +x "${DISPLAY_SCRIPT}"
        echo "Enabled executable permission: scripts/display/show_image.py"
    fi

    if [[ -f "${ASSETS_DIR}/goobo_startup_480x640.png" ]]; then
        echo "Found default startup image:"
        echo "  ${ASSETS_DIR}/goobo_startup_480x640.png"
    else
        echo "WARNING: default startup image not found:"
        echo "  ${ASSETS_DIR}/goobo_startup_480x640.png"
    fi
else
    echo "WARNING: assets directory not found:"
    echo "  ${ASSETS_DIR}"
fi

echo
echo "Goobo environment installation finished."
echo "Please reboot before using hardware tools without sudo:"
echo "  sudo reboot"
echo
echo "After reboot, you can show the startup image with:"
echo "  ${REPO_DIR}/scripts/display/show_image.py"
