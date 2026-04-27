#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: run this installer with sudo."
    echo "Example: sudo ./install_environment.sh"
    exit 1
fi

echo "Updating apt package index..."
apt update

echo "Installing Goobo system dependencies..."
apt-get install -y \
    openssl \
    build-essential \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    python3 \
    python3-dev \
    python3-pip \
    python3-setuptools \
    python3-numpy \
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
    portaudio19-dev

echo "Installing Goobo Python audio dependency..."
python3 -m pip install --break-system-packages sounddevice

TARGET_USER="${SUDO_USER:-$USER}"
HARDWARE_GROUPS=(dialout video audio render gpio i2c spi)

echo "Adding ${TARGET_USER} to hardware access groups..."
for group in "${HARDWARE_GROUPS[@]}"; do
    if getent group "${group}" >/dev/null; then
        usermod -aG "${group}" "${TARGET_USER}"
        echo "Added ${TARGET_USER} to ${group}"
    fi
done

echo "Goobo environment installation finished."
echo "Reboot or log out and log back in before running hardware tools without sudo."
