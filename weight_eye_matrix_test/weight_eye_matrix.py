#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, Tuple

BASE_DIR = Path(__file__).resolve().parent
GOOBO_DIR = BASE_DIR.parent

# Reuse the sibling hardware test modules without copying their code here.
sys.path.insert(0, str(GOOBO_DIR / "hx711_test"))
sys.path.insert(0, str(GOOBO_DIR / "eye_matrix_test"))
sys.path.insert(0, str(GOOBO_DIR / "bus_servo_test"))

from bus_servo import BusServo  # noqa: E402
from eye_matrix_8x8 import EyeMatrix  # noqa: E402
from hx711 import HX711  # noqa: E402

RGB = Tuple[int, int, int]
ServoPositions = dict[int, tuple[float, float]]
Frame = list[tuple[int, int, RGB]]
LoggerConfig = tuple[bool, Path, int]


def read_config(path: Path) -> configparser.ConfigParser:
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    config = configparser.ConfigParser()
    config.read(path, encoding="utf-8")
    return config


def parse_rgb(value: str) -> RGB:
    parts = [part.strip() for part in value.split(",")]
    if len(parts) != 3:
        raise ValueError(f"RGB color must have three comma-separated values: {value}")

    red, green, blue = (int(part) for part in parts)
    rgb = (red, green, blue)
    if any(channel < 0 or channel > 255 for channel in rgb):
        raise ValueError(f"RGB color values must be 0..255: {value}")

    return rgb


def mirror(points: Iterable[tuple[int, int]], left_width: int = 3, gap: int = 2) -> list[tuple[int, int]]:
    left = list(points)
    x_offset = left_width + gap
    return left + [(x + x_offset, y) for x, y in left]


def double_eye_shapes() -> list[list[tuple[int, int]]]:
    open_eye = mirror(
        [
            (0, 2), (1, 1), (2, 2),
            (0, 3), (1, 3), (2, 3),
            (0, 4), (1, 5), (2, 4),
        ]
    )
    narrow_eye = mirror([(0, 3), (1, 3), (2, 3)])
    return [open_eye, narrow_eye, [], narrow_eye, open_eye]


def single_eye_shapes() -> list[list[tuple[int, int]]]:
    open_eye = [
        (1, 3), (2, 2), (3, 1), (4, 1), (5, 2), (6, 3),
        (1, 4), (2, 5), (3, 6), (4, 6), (5, 5), (6, 4),
    ]
    half_open_eye = [
        (1, 3), (2, 3), (3, 2), (4, 2), (5, 3), (6, 3),
        (1, 4), (2, 4), (3, 5), (4, 5), (5, 4), (6, 4),
    ]
    narrow_eye = [(1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4)]
    return [open_eye, half_open_eye, narrow_eye, [], narrow_eye, half_open_eye, open_eye]


def pixels_to_points(pixel_indexes: Iterable[int], width: int = 8) -> list[tuple[int, int]]:
    return [(index % width, index // width) for index in pixel_indexes]


def expression_frames(expression_id: int, eye_color: RGB) -> list[Frame]:
    if expression_id == 1:
        # Extracted from /home/neurobo/test/DEMO.ino eyesLight(): 12..14 and 52..54.
        shapes = [pixels_to_points([12, 13, 14, 52, 53, 54])]
    elif expression_id == 2:
        shapes = single_eye_shapes()
    elif expression_id == 3:
        shapes = double_eye_shapes()
    else:
        raise ValueError("display.expression_id must be 1, 2 or 3")

    return [[(x, y, eye_color) for x, y in shape] for shape in shapes]


def parse_int_list(value: str) -> list[int]:
    ids = [int(part.strip(), 0) for part in value.split(",") if part.strip()]
    if not ids:
        raise ValueError("servo_bus.move_order cannot be empty")
    return ids


def parse_logger_config(config: configparser.ConfigParser) -> LoggerConfig:
    if not config.has_section("logging"):
        return (False, BASE_DIR / "weight_eye_matrix.log", 1048576)

    return (
        config.getboolean("logging", "enabled"),
        Path(config.get("logging", "path")).expanduser(),
        config.getint("logging", "max_bytes"),
    )


def write_log(logger_config: LoggerConfig, message: str) -> None:
    enabled, path, max_bytes = logger_config
    if not enabled:
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and path.stat().st_size >= max_bytes:
        path.write_text("", encoding="utf-8")

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with path.open("a", encoding="utf-8") as log_file:
        log_file.write(f"{timestamp} {message}\n")


def parse_servo_positions(config: configparser.ConfigParser) -> ServoPositions:
    if not config.has_section("servo_positions"):
        raise ValueError("Missing [servo_positions] config section")

    positions: ServoPositions = {}
    for servo_id_text, angles_text in config.items("servo_positions"):
        servo_id = int(servo_id_text, 0)
        parts = [part.strip() for part in angles_text.split(",")]
        if len(parts) != 2:
            raise ValueError(f"servo {servo_id} must be configured as initial_degrees,target_degrees")
        positions[servo_id] = (float(parts[0]), float(parts[1]))

    return positions


def move_servos(
    bus: BusServo,
    positions: ServoPositions,
    move_order: list[int],
    use_initial_angle: bool,
    move_time_ms: int,
    speed: int,
    gap_seconds: float,
) -> None:
    target_name = "initial" if use_initial_angle else "target"
    for index, servo_id in enumerate(move_order):
        if servo_id not in positions:
            raise ValueError(f"servo id {servo_id} is in move_order but missing from servo_positions")

        initial_degrees, target_degrees = positions[servo_id]
        degrees = initial_degrees if use_initial_angle else target_degrees
        bus.move_to_raw(servo_id, bus.degrees_to_raw(degrees), time_ms=move_time_ms, speed=speed)
        print(f"servo id={servo_id} move {target_name} degrees={degrees:.2f}")

        if index < len(move_order) - 1:
            time.sleep(gap_seconds)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Drive 8x8 eye matrix from HX711 weight threshold.")
    parser.add_argument(
        "--config",
        type=Path,
        default=BASE_DIR / "config.ini",
        help="Path to config file",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    config = read_config(args.config.expanduser().resolve())

    hx = HX711(
        dout_pin=config.getint("hx711", "dout_pin"),
        pd_sck_pin=config.getint("hx711", "sck_pin"),
        gain=config.getint("hx711", "gain"),
    )
    matrix = EyeMatrix(
        pin=config.getint("matrix", "pin"),
        freq_hz=config.getint("matrix", "freq_hz"),
        dma=config.getint("matrix", "dma"),
        brightness=max(0, min(255, config.getint("matrix", "brightness"))),
        invert=config.getboolean("matrix", "invert"),
        channel=config.getint("matrix", "channel"),
        zigzag=config.getboolean("matrix", "zigzag"),
        flip_x=config.getboolean("matrix", "flip_x"),
        flip_y=config.getboolean("matrix", "flip_y"),
    )

    threshold = config.getfloat("display", "threshold")
    poll_interval = config.getfloat("display", "poll_interval")
    blink_delay = 1.0 / max(1, config.getint("display", "blink_fps"))
    full_color = parse_rgb(config.get("display", "full_color"))
    background_color = parse_rgb(config.get("display", "background_color"))
    logger_config = parse_logger_config(config)
    frames = expression_frames(
        expression_id=config.getint("display", "expression_id"),
        eye_color=parse_rgb(config.get("display", "eye_color")),
    )
    frame_index = 0
    mode = None
    weight_state = None
    servo_state = None
    servo_bus = None
    servo_enabled = config.getboolean("servo_bus", "enabled")
    servo_positions: ServoPositions = {}
    servo_move_order: list[int] = []
    servo_move_time_ms = 0
    servo_speed = 0
    servo_gap_seconds = 0.0

    try:
        if servo_enabled:
            servo_positions = parse_servo_positions(config)
            servo_move_order = parse_int_list(config.get("servo_bus", "move_order"))
            servo_move_time_ms = config.getint("servo_bus", "move_time_ms")
            servo_speed = config.getint("servo_bus", "speed")
            servo_gap_seconds = config.getfloat("servo_bus", "move_gap_seconds")
            servo_bus = BusServo(
                port=config.get("servo_bus", "port"),
                baud=config.getint("servo_bus", "baud"),
            )
            if config.getboolean("servo_bus", "enable_torque"):
                for servo_id in servo_move_order:
                    servo_bus.enable_torque(servo_id, True)

        print("Keep the scale empty, tare start...")
        hx.tare(times=config.getint("hx711", "tare_times"))
        hx.set_scale(config.getfloat("hx711", "scale"))
        print(f"offset={hx.offset:.2f}, threshold={threshold:.3f}")
        write_log(logger_config, f"event=start offset={hx.offset:.2f} threshold={threshold:.3f}")

        while True:
            weight = hx.get_weight(times=config.getint("hx711", "read_times"))
            print(f"weight={weight:8.3f}")

            if weight > threshold:
                if weight_state != "high":
                    write_log(
                        logger_config,
                        f"state=high weight={weight:.3f} threshold={threshold:.3f} action=full_light_initial_servos",
                    )
                    weight_state = "high"
                if mode != "full":
                    matrix.draw_pixels([], background=full_color)
                    mode = "full"
                if servo_bus is not None and servo_state != "initial":
                    move_servos(
                        bus=servo_bus,
                        positions=servo_positions,
                        move_order=servo_move_order,
                        use_initial_angle=True,
                        move_time_ms=servo_move_time_ms,
                        speed=servo_speed,
                        gap_seconds=servo_gap_seconds,
                    )
                    servo_state = "initial"
                time.sleep(poll_interval)
                continue

            if weight_state != "low":
                write_log(
                    logger_config,
                    f"state=low weight={weight:.3f} threshold={threshold:.3f} action=expression_target_servos",
                )
                weight_state = "low"
            mode = "blink"
            matrix.draw_pixels(frames[frame_index % len(frames)], background=background_color)
            frame_index += 1
            if servo_bus is not None and servo_state != "target":
                move_servos(
                    bus=servo_bus,
                    positions=servo_positions,
                    move_order=servo_move_order,
                    use_initial_angle=False,
                    move_time_ms=servo_move_time_ms,
                    speed=servo_speed,
                    gap_seconds=servo_gap_seconds,
                )
                servo_state = "target"
            time.sleep(blink_delay)

    except KeyboardInterrupt:
        print("Exit")

    finally:
        matrix.clear()
        hx.cleanup()
        if servo_bus is not None:
            servo_bus.close()


if __name__ == "__main__":
    main()
