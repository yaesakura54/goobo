#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import sys
import time
from pathlib import Path

from bus_servo import DEFAULT_BAUD, BusServo, parse_id_list


def main() -> None:
    parser = argparse.ArgumentParser(description="Record current bus-servo positions.")
    parser.add_argument("--port", required=True, help="Serial port, for example /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"Serial baud rate, default {DEFAULT_BAUD}")
    parser.add_argument("--ids", default="1,2,3,4,5", help="Servo IDs to read, default 1,2,3,4,5")
    parser.add_argument("--hz", type=float, default=10.0, help="Read frequency, default 10 Hz")
    parser.add_argument("--duration", type=float, default=0.0, help="Seconds to record. 0 means until Ctrl+C")
    parser.add_argument("--csv", type=Path, help="Optional CSV output path")
    args = parser.parse_args()

    servo_ids = parse_id_list(args.ids)
    interval = 1.0 / args.hz if args.hz > 0 else 0.1
    deadline = time.monotonic() + args.duration if args.duration > 0 else None

    csv_file = None
    writer = None
    if args.csv:
        csv_file = args.csv.open("w", newline="")
        fields = ["timestamp"]
        for servo_id in servo_ids:
            fields.extend([f"id{servo_id}_raw", f"id{servo_id}_deg"])
        writer = csv.DictWriter(csv_file, fieldnames=fields)
        writer.writeheader()

    print(f"Recording ids={servo_ids} on {args.port}. Press Ctrl+C to stop.")

    try:
        with BusServo(args.port, args.baud) as bus:
            while deadline is None or time.monotonic() < deadline:
                t0 = time.time()
                row: dict[str, float | int] = {"timestamp": t0}
                parts = [time.strftime("%H:%M:%S", time.localtime(t0))]

                for servo_id in servo_ids:
                    raw = bus.read_position(servo_id)
                    deg = round(bus.raw_to_degrees(raw), 2)
                    row[f"id{servo_id}_raw"] = raw
                    row[f"id{servo_id}_deg"] = deg
                    parts.append(f"id{servo_id}: raw={raw} deg={deg:.2f}")

                print(" | ".join(parts))
                if writer is not None:
                    writer.writerow(row)
                    csv_file.flush()

                elapsed = time.time() - t0
                time.sleep(max(0.0, interval - elapsed))
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        if csv_file is not None:
            csv_file.close()
            print(f"CSV written: {args.csv}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
