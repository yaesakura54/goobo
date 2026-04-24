#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time

from bus_servo import DEFAULT_BAUD, POSITION_MAX, BusServo


def cmd_scan(bus: BusServo, args: argparse.Namespace) -> None:
    found: list[int] = []
    for servo_id in range(args.start, args.end + 1):
        try:
            bus.ping(servo_id)
        except Exception:
            continue
        found.append(servo_id)
        print(f"found id={servo_id}")
    if not found:
        print("no servos found")


def cmd_ping(bus: BusServo, args: argparse.Namespace) -> None:
    bus.ping(args.id)
    print(f"id={args.id} responded")


def cmd_status(bus: BusServo, args: argparse.Namespace) -> None:
    status = bus.read_status_values(args.id)
    for key, value in status.items():
        print(f"{key}: {value}")


def cmd_torque(bus: BusServo, args: argparse.Namespace) -> None:
    enabled = args.state == "on"
    bus.enable_torque(args.id, enabled)
    print(f"id={args.id} torque={'on' if enabled else 'off'}")


def cmd_move(bus: BusServo, args: argparse.Namespace) -> None:
    if args.degrees is not None:
        raw = bus.degrees_to_raw(args.degrees)
    else:
        raw = args.raw
    if raw is None:
        raise ValueError("move requires --raw or --degrees")
    if not 0 <= raw <= POSITION_MAX:
        raise ValueError(f"raw position must be 0..{POSITION_MAX}")

    if args.enable_torque:
        bus.enable_torque(args.id, True)
        time.sleep(0.05)
    bus.move_to_raw(args.id, raw, args.time_ms, args.speed)
    print(f"id={args.id} move target raw={raw} deg={bus.raw_to_degrees(raw):.2f}")


def cmd_raw_read(bus: BusServo, args: argparse.Namespace) -> None:
    data = bus.read(args.id, args.address, args.size)
    print(" ".join(f"0x{b:02x}" for b in data))


def cmd_raw_write(bus: BusServo, args: argparse.Namespace) -> None:
    values = [int(v, 0) & 0xFF for v in args.values]
    bus.write(args.id, args.address, values)
    print(f"id={args.id} wrote {len(values)} byte(s) at address {args.address}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Debug Feetech/ST-series bus servos.")
    parser.add_argument("--port", required=True, help="Serial port, for example /dev/ttyUSB0")
    parser.add_argument("--baud", type=int, default=DEFAULT_BAUD, help=f"Serial baud rate, default {DEFAULT_BAUD}")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="Scan IDs with ping")
    scan.add_argument("--start", type=int, default=1)
    scan.add_argument("--end", type=int, default=20)
    scan.set_defaults(func=cmd_scan)

    ping = sub.add_parser("ping", help="Ping one servo")
    ping.add_argument("--id", type=int, required=True)
    ping.set_defaults(func=cmd_ping)

    status = sub.add_parser("status", help="Read position, speed, load, voltage, temperature and moving flag")
    status.add_argument("--id", type=int, required=True)
    status.set_defaults(func=cmd_status)

    torque = sub.add_parser("torque", help="Enable or disable torque")
    torque.add_argument("--id", type=int, required=True)
    torque.add_argument("state", choices=["on", "off"])
    torque.set_defaults(func=cmd_torque)

    move = sub.add_parser("move", help="Move one servo to a raw position or degree value")
    move.add_argument("--id", type=int, required=True)
    target = move.add_mutually_exclusive_group(required=True)
    target.add_argument("--raw", type=int)
    target.add_argument("--degrees", type=float)
    move.add_argument("--time-ms", type=int, default=1000)
    move.add_argument("--speed", type=int, default=0)
    move.add_argument("--enable-torque", action="store_true")
    move.set_defaults(func=cmd_move)

    raw_read = sub.add_parser("raw-read", help="Read raw register bytes")
    raw_read.add_argument("--id", type=int, required=True)
    raw_read.add_argument("--address", type=int, required=True)
    raw_read.add_argument("--size", type=int, required=True)
    raw_read.set_defaults(func=cmd_raw_read)

    raw_write = sub.add_parser("raw-write", help="Write raw register bytes")
    raw_write.add_argument("--id", type=int, required=True)
    raw_write.add_argument("--address", type=int, required=True)
    raw_write.add_argument("values", nargs="+", help="Byte values, for example 0x01 0x02")
    raw_write.set_defaults(func=cmd_raw_write)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    with BusServo(args.port, args.baud) as bus:
        args.func(bus, args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)
