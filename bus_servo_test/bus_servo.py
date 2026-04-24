#!/usr/bin/env python3
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

import serial


BROADCAST_ID = 0xFE

INST_PING = 0x01
INST_READ = 0x02
INST_WRITE = 0x03

REG_ID = 5
REG_LOCK = 55
REG_TORQUE_ENABLE = 40
REG_GOAL_POSITION = 42
REG_PRESENT_POSITION = 56
REG_PRESENT_SPEED = 58
REG_PRESENT_LOAD = 60
REG_PRESENT_VOLTAGE = 62
REG_PRESENT_TEMPERATURE = 63
REG_MOVING = 66

DEFAULT_BAUD = 1_000_000
POSITION_MAX = 4095


class ServoError(RuntimeError):
    pass


@dataclass(frozen=True)
class StatusPacket:
    servo_id: int
    error: int
    params: bytes


class BusServo:
    def __init__(self, port: str, baud: int = DEFAULT_BAUD, timeout: float = 0.08):
        self.serial = serial.Serial(
            port=port,
            baudrate=baud,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=timeout,
        )

    def close(self) -> None:
        self.serial.close()

    def __enter__(self) -> "BusServo":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    @staticmethod
    def checksum(values: Iterable[int]) -> int:
        return (~sum(values)) & 0xFF

    @staticmethod
    def word_to_bytes(value: int) -> list[int]:
        return [value & 0xFF, (value >> 8) & 0xFF]

    @staticmethod
    def bytes_to_word(data: bytes) -> int:
        if len(data) != 2:
            raise ServoError(f"expected 2 bytes, got {len(data)}")
        return data[0] | (data[1] << 8)

    @staticmethod
    def raw_to_degrees(raw: int) -> float:
        return raw * 360.0 / POSITION_MAX

    @staticmethod
    def degrees_to_raw(degrees: float) -> int:
        raw = round(degrees * POSITION_MAX / 360.0)
        return max(0, min(POSITION_MAX, raw))

    def send(self, servo_id: int, instruction: int, params: Iterable[int], expect_status: bool = True) -> StatusPacket | None:
        param_list = [p & 0xFF for p in params]
        length = len(param_list) + 2
        body = [servo_id & 0xFF, length, instruction & 0xFF, *param_list]
        packet = bytes([0xFF, 0xFF, *body, self.checksum(body)])

        self.serial.reset_input_buffer()
        self.serial.write(packet)
        self.serial.flush()

        if not expect_status or servo_id == BROADCAST_ID:
            return None
        return self.read_status(expected_id=servo_id)

    def read_status(self, expected_id: int | None = None) -> StatusPacket:
        deadline = time.monotonic() + max(self.serial.timeout or 0.08, 0.08)
        window = bytearray()

        while time.monotonic() < deadline:
            byte = self.serial.read(1)
            if not byte:
                continue
            window.append(byte[0])
            if len(window) > 2:
                window = window[-2:]
            if window == b"\xff\xff":
                break
        else:
            raise ServoError("timeout waiting for packet header")

        head = self.serial.read(3)
        if len(head) != 3:
            raise ServoError("timeout waiting for status header")

        servo_id, length, error = head
        rest = self.serial.read(length - 1)
        if len(rest) != length - 1:
            raise ServoError("timeout waiting for status body")

        params = rest[:-1]
        recv_checksum = rest[-1]
        expected_checksum = self.checksum([servo_id, length, error, *params])
        if recv_checksum != expected_checksum:
            raise ServoError(f"bad checksum: got 0x{recv_checksum:02x}, expected 0x{expected_checksum:02x}")

        if expected_id is not None and servo_id != expected_id:
            raise ServoError(f"unexpected servo id {servo_id}, expected {expected_id}")

        if error:
            raise ServoError(f"servo {servo_id} returned error 0x{error:02x}")

        return StatusPacket(servo_id=servo_id, error=error, params=bytes(params))

    def ping(self, servo_id: int) -> bool:
        self.send(servo_id, INST_PING, [])
        return True

    def read(self, servo_id: int, address: int, size: int) -> bytes:
        status = self.send(servo_id, INST_READ, [address, size])
        if status is None:
            raise ServoError("read did not return a status packet")
        if len(status.params) != size:
            raise ServoError(f"read {len(status.params)} bytes, expected {size}")
        return status.params

    def write(self, servo_id: int, address: int, data: Iterable[int], expect_status: bool = True) -> None:
        self.send(servo_id, INST_WRITE, [address, *data], expect_status=expect_status)

    def write_byte(self, servo_id: int, address: int, value: int, expect_status: bool = True) -> None:
        self.write(servo_id, address, [value], expect_status=expect_status)

    def write_word(self, servo_id: int, address: int, value: int, expect_status: bool = True) -> None:
        self.write(servo_id, address, self.word_to_bytes(value), expect_status=expect_status)

    def set_id(self, current_id: int, new_id: int, unlock: bool = True) -> None:
        if not 0 <= current_id <= 253 and current_id != BROADCAST_ID:
            raise ServoError(f"invalid current id: {current_id}")
        if not 1 <= new_id <= 253:
            raise ServoError(f"invalid new id: {new_id}")

        expect_status = current_id != BROADCAST_ID
        if unlock:
            self.write_byte(current_id, REG_LOCK, 0, expect_status=expect_status)
        self.write_byte(current_id, REG_ID, new_id, expect_status=expect_status)
        if unlock:
            time.sleep(0.05)
            self.write_byte(new_id, REG_LOCK, 1, expect_status=True)

    def read_position(self, servo_id: int) -> int:
        return self.bytes_to_word(self.read(servo_id, REG_PRESENT_POSITION, 2))

    def read_status_values(self, servo_id: int) -> dict[str, int | float | bool]:
        raw_position = self.read_position(servo_id)
        speed = self.bytes_to_word(self.read(servo_id, REG_PRESENT_SPEED, 2))
        load = self.bytes_to_word(self.read(servo_id, REG_PRESENT_LOAD, 2))
        voltage_raw = self.read(servo_id, REG_PRESENT_VOLTAGE, 1)[0]
        temperature_c = self.read(servo_id, REG_PRESENT_TEMPERATURE, 1)[0]
        moving = bool(self.read(servo_id, REG_MOVING, 1)[0])
        return {
            "id": servo_id,
            "raw_position": raw_position,
            "degrees": round(self.raw_to_degrees(raw_position), 2),
            "speed_raw": speed,
            "load_raw": load,
            "voltage_v": round(voltage_raw / 10.0, 2),
            "temperature_c": temperature_c,
            "moving": moving,
        }

    def enable_torque(self, servo_id: int, enabled: bool) -> None:
        self.write_byte(servo_id, REG_TORQUE_ENABLE, 1 if enabled else 0)

    def move_to_raw(self, servo_id: int, raw_position: int, time_ms: int = 1000, speed: int = 0) -> None:
        raw_position = max(0, min(POSITION_MAX, raw_position))
        time_ms = max(0, min(65535, time_ms))
        speed = max(0, min(65535, speed))
        data = [
            *self.word_to_bytes(raw_position),
            *self.word_to_bytes(time_ms),
            *self.word_to_bytes(speed),
        ]
        self.write(servo_id, REG_GOAL_POSITION, data)


def parse_id_list(text: str) -> list[int]:
    ids: list[int] = []
    for part in text.split(","):
        value = part.strip()
        if not value:
            continue
        servo_id = int(value, 0)
        if not 1 <= servo_id <= 253:
            raise ValueError(f"invalid servo id: {servo_id}")
        ids.append(servo_id)
    if not ids:
        raise ValueError("empty id list")
    return ids
