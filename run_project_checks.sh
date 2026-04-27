#!/usr/bin/env bash
set -uo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_HARDWARE=false
FAILURES=0

SERVO_PORT="${SERVO_PORT:-/dev/ttyACM0}"
SERVO_BAUD="${SERVO_BAUD:-1000000}"
SERVO_START_ID="${SERVO_START_ID:-1}"
SERVO_END_ID="${SERVO_END_ID:-5}"

usage() {
    cat <<EOF
Usage:
  ./run_project_checks.sh
  ./run_project_checks.sh --hardware

Environment variables for --hardware:
  SERVO_PORT      default: /dev/ttyACM0
  SERVO_BAUD      default: 1000000
  SERVO_START_ID  default: 1
  SERVO_END_ID    default: 5
EOF
}

case "${1:-}" in
    "")
        ;;
    "--hardware")
        RUN_HARDWARE=true
        ;;
    "-h"|"--help")
        usage
        exit 0
        ;;
    *)
        usage
        exit 2
        ;;
esac

run_check() {
    local label="$1"
    shift

    echo
    echo "==> ${label}"
    if "$@"; then
        echo "PASS: ${label}"
    else
        local status=$?
        echo "FAIL: ${label} (exit ${status})"
        FAILURES=$((FAILURES + 1))
    fi
}

run_shell_check() {
    local label="$1"
    local script="$2"

    run_check "${label}" bash -c "${script}"
}

cd "${ROOT_DIR}" || exit 1

run_check "python files compile" python3 - <<'PY'
from pathlib import Path

skip_dirs = {".git", ".venv", "venv", "__pycache__"}
for path in sorted(Path(".").rglob("*.py")):
    if any(part in skip_dirs for part in path.parts):
        continue
    compile(path.read_bytes(), str(path), "exec")
    print(path)
PY

run_shell_check "shell scripts syntax" 'set -euo pipefail; while IFS= read -r -d "" file; do echo "$file"; bash -n "$file"; done < <(find . -name "*.sh" -print0)'

run_shell_check "required commands exist" 'set -euo pipefail; for cmd in python3 rpicam-still rpicam-vid ffmpeg; do command -v "$cmd"; done'

run_check "python hardware dependency imports" python3 - <<'PY'
import RPi.GPIO
import numpy
import rpi_ws281x
import serial
import sounddevice

print("Python hardware dependencies import successfully.")
PY

run_check "weight_eye_matrix config parses" python3 - <<'PY'
import configparser
from pathlib import Path

config_path = Path("weight_eye_matrix_test/config.ini")
config = configparser.ConfigParser()
loaded = config.read(config_path)
if not loaded:
    raise SystemExit(f"Config not found: {config_path}")

required = {
    "hx711": ("dout_pin", "sck_pin", "gain", "scale", "tare_times", "read_times"),
    "matrix": ("pin", "brightness", "freq_hz", "dma", "invert", "channel", "zigzag", "flip_x", "flip_y"),
    "display": ("threshold", "expression_id", "full_color", "eye_color", "background_color"),
    "servo_bus": ("enabled", "port", "baud", "move_time_ms", "move_order"),
    "servo_positions": (),
    "logging": ("enabled", "path", "max_bytes"),
}

for section, keys in required.items():
    if not config.has_section(section):
        raise SystemExit(f"Missing section: {section}")
    for key in keys:
        if not config.has_option(section, key):
            raise SystemExit(f"Missing option: {section}.{key}")

if len(config.items("servo_positions")) == 0:
    raise SystemExit("Missing servo positions.")

print(f"Loaded {config_path}")
PY

run_check "camera_capture help" python3 camera_test/camera_capture.py --help
run_check "camera_video help" python3 camera_test/camera_video.py --help
run_check "mic_record help" python3 audio_test/mic_record.py --help
run_check "speaker_play help" python3 audio_test/speaker_play.py --help
run_check "eye_matrix help" python3 eye_matrix_test/eye_matrix_8x8.py --help
run_check "bus_servo debug help" python3 bus_servo_test/debug_servo.py --help
run_check "bus_servo set ids help" python3 bus_servo_test/set_servo_ids.py --help
run_check "bus_servo record angles help" python3 bus_servo_test/record_angles.py --help
run_check "weight_eye_matrix help" python3 weight_eye_matrix_test/weight_eye_matrix.py --help

if [[ "${RUN_HARDWARE}" == "true" ]]; then
    run_check "microphone device list" python3 audio_test/mic_record.py --list-devices
    run_check "speaker device list" python3 audio_test/speaker_play.py --list-devices
    run_check "rpicam-still version" rpicam-still --version
    run_check "rpicam-vid version" rpicam-vid --version
    run_check "ffmpeg version" ffmpeg -version
    run_check "hx711 one raw read" python3 - <<'PY'
import configparser
import sys
from pathlib import Path

sys.path.insert(0, str(Path("hx711_test").resolve()))
from hx711 import HX711

config = configparser.ConfigParser()
config.read("weight_eye_matrix_test/config.ini")

hx = HX711(
    dout_pin=config.getint("hx711", "dout_pin"),
    pd_sck_pin=config.getint("hx711", "sck_pin"),
    gain=config.getint("hx711", "gain"),
)
try:
    print(hx.read_raw(times=1))
finally:
    hx.cleanup()
PY
    run_check "bus servo scan" python3 bus_servo_test/debug_servo.py --port "${SERVO_PORT}" --baud "${SERVO_BAUD}" scan --start "${SERVO_START_ID}" --end "${SERVO_END_ID}"
    run_check "eye matrix one frame" sudo python3 eye_matrix_test/eye_matrix_8x8.py --state neutral --once --brightness 8
else
    echo
    echo "Skipping hardware actions. Use ./run_project_checks.sh --hardware to test devices."
fi

echo
if [[ "${FAILURES}" -eq 0 ]]; then
    echo "All project checks passed."
    exit 0
fi

echo "${FAILURES} project check(s) failed."
exit 1
