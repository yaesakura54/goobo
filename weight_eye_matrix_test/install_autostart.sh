#!/usr/bin/env bash
set -euo pipefail

SERVICE_NAME="goobo-weight-eye-matrix.service"
SERVICE_PATH="/etc/systemd/system/${SERVICE_NAME}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_SCRIPT="${SCRIPT_DIR}/weight_eye_matrix.py"
CONFIG_FILE="${SCRIPT_DIR}/config.ini"

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: run this installer with sudo."
    echo "Example: sudo ${BASH_SOURCE[0]}"
    exit 1
fi

if [[ ! -f "${APP_SCRIPT}" ]]; then
    echo "ERROR: app script not found: ${APP_SCRIPT}"
    exit 1
fi

if [[ ! -f "${CONFIG_FILE}" ]]; then
    echo "ERROR: config file not found: ${CONFIG_FILE}"
    exit 1
fi

cat > "${SERVICE_PATH}" <<SERVICE
[Unit]
Description=Goobo weight, eye matrix and servo linkage
DefaultDependencies=no
After=local-fs.target dev-ttyACM0.device
Requires=dev-ttyACM0.device
Before=multi-user.target

[Service]
Type=simple
User=root
WorkingDirectory=${SCRIPT_DIR}
ExecStart=/usr/bin/python3 -u ${APP_SCRIPT} --config ${CONFIG_FILE}

[Install]
WantedBy=basic.target
SERVICE

systemctl daemon-reload
systemctl enable "${SERVICE_NAME}"
systemctl start "${SERVICE_NAME}"

echo "Installed, enabled and started ${SERVICE_NAME}."
