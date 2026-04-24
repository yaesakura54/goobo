#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time

from bus_servo import BROADCAST_ID, DEFAULT_BAUD, BusServo


DEFAULT_MOTORS = [
    ("wrist_pitch", 5),
    ("wrist_roll", 4),
    ("elbow_pitch", 3),
    ("base_pitch", 2),
    ("base_yaw", 1),
]


def parse_motor_map(text: str) -> list[tuple[str, int]]:
    motors: list[tuple[str, int]] = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" not in item:
            raise ValueError(f"invalid motor mapping: {item}")
        name, id_text = item.split(":", 1)
        servo_id = int(id_text, 0)
        if not 1 <= servo_id <= 253:
            raise ValueError(f"invalid servo id: {servo_id}")
        motors.append((name.strip(), servo_id))
    if not motors:
        raise ValueError("empty motor mapping")
    return motors


def main() -> None:
    parser = argparse.ArgumentParser(description="Set Feetech/ST-series bus servo IDs one motor at a time.")
    parser.add_argument("--port", required=True, help="Serial port, for example /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"Serial baud rate, default {DEFAULT_BAUD}")
    parser.add_argument("--current-id", type=int, default=1, help="Current servo ID before setup, default 1")
    parser.add_argument(
        "--broadcast",
        action="store_true",
        help="Use broadcast write for ID setup. Only use when exactly one servo is connected.",
    )
    parser.add_argument(
        "--motors",
        default=",".join(f"{name}:{servo_id}" for name, servo_id in DEFAULT_MOTORS),
        help="Motor mapping, for example base_yaw:1,base_pitch:2",
    )
    args = parser.parse_args()

    motors = parse_motor_map(args.motors)
    current_id = BROADCAST_ID if args.broadcast else args.current_id

    print("Set servo IDs. Connect exactly one servo before each step.")
    print(f"Port: {args.port}, baud: {args.baud}, current_id: {'broadcast' if args.broadcast else args.current_id}")

    with BusServo(args.port, args.baud) as bus:
        for name, target_id in motors:
            input(f"\nConnect only '{name}' servo, then press ENTER to set id={target_id}...")
            bus.set_id(current_id, target_id)
            time.sleep(0.15)
            bus.ping(target_id)
            print(f"OK: '{name}' is responding as id={target_id}")

    print("\nDone.")


if __name__ == "__main__":
    main()
