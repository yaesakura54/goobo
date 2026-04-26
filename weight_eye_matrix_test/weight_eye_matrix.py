#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import math
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
ServoDegrees = dict[int, float]


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


def strip_indexes_to_points(
    pixel_indexes: Iterable[int],
    width: int = 8,
    height: int = 8,
    zigzag: bool = True,
    flip_x: bool = False,
    flip_y: bool = False,
) -> list[tuple[int, int]]:
    points = []
    for index in pixel_indexes:
        x = index % width
        y = index // width
        if not 0 <= y < height:
            raise ValueError(f"pixel index out of range: {index}")
        if zigzag and (y % 2 == 1):
            x = width - 1 - x
        if flip_y:
            y = height - 1 - y
        if flip_x:
            x = width - 1 - x
        points.append((x, y))
    return points


def expression_frames(
    expression_id: int,
    eye_color: RGB,
    zigzag: bool,
    flip_x: bool,
    flip_y: bool,
) -> list[Frame]:
    if expression_id == 1:
        # Extracted from /home/neurobo/test/DEMO.ino eyesLight(): 12..14 and 52..54.
        shapes = [
            strip_indexes_to_points(
                [12, 13, 14, 52, 53, 54],
                zigzag=zigzag,
                flip_x=flip_x,
                flip_y=flip_y,
            )
        ]
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


def parse_logger_config(config: configparser.ConfigParser, config_dir: Path) -> LoggerConfig:
    if not config.has_section("logging"):
        return (False, BASE_DIR / "weight_eye_matrix.log", 1048576)

    log_path = Path(config.get("logging", "path")).expanduser()
    if not log_path.is_absolute():
        log_path = config_dir / log_path

    return (
        config.getboolean("logging", "enabled"),
        log_path,
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


def parse_startup_position(config: configparser.ConfigParser) -> str:
    startup_position = config.get("servo_bus", "startup_position", fallback="none").strip().lower()
    if startup_position not in {"initial", "target", "none"}:
        raise ValueError("servo_bus.startup_position must be initial, target or none")
    return startup_position


def parse_move_mode(config: configparser.ConfigParser) -> str:
    move_mode = config.get("servo_bus", "move_mode", fallback="together").strip().lower()
    if move_mode not in {"together", "sequence"}:
        raise ValueError("servo_bus.move_mode must be together or sequence")
    return move_mode


def read_servo_degrees(bus: BusServo, move_order: list[int]) -> ServoDegrees:
    return {
        servo_id: bus.raw_to_degrees(bus.read_position(servo_id))
        for servo_id in move_order
    }


def hold_current_servos(bus: BusServo, current_degrees: ServoDegrees, move_order: list[int]) -> None:
    for servo_id in move_order:
        degrees = current_degrees[servo_id]
        bus.move_to_raw(servo_id, bus.degrees_to_raw(degrees), time_ms=0, speed=0)


def move_servos(
    bus: BusServo,
    positions: ServoPositions,
    move_order: list[int],
    use_initial_angle: bool,
    move_time_ms: int,
    speed: int,
    gap_seconds: float,
    move_mode: str,
) -> None:
    target_name = "initial" if use_initial_angle else "target"
    for index, servo_id in enumerate(move_order):
        if servo_id not in positions:
            raise ValueError(f"servo id {servo_id} is in move_order but missing from servo_positions")

        initial_degrees, target_degrees = positions[servo_id]
        degrees = initial_degrees if use_initial_angle else target_degrees
        bus.move_to_raw(servo_id, bus.degrees_to_raw(degrees), time_ms=move_time_ms, speed=speed)
        print(f"servo id={servo_id} move {target_name} degrees={degrees:.2f}")

        if move_mode == "sequence" and index < len(move_order) - 1:
            time.sleep(gap_seconds)


def ramp_startup_servos(
    bus: BusServo,
    positions: ServoPositions,
    move_order: list[int],
    use_initial_angle: bool,
    step_degrees: float,
    step_delay: float,
    step_time_ms: int,
    speed: int,
    gap_seconds: float,
    move_mode: str,
    current_degrees: ServoDegrees | None = None,
    config_prefix: str = "servo_bus.startup",
) -> None:
    if step_degrees <= 0:
        raise ValueError(f"{config_prefix}_step_degrees must be > 0")
    if step_delay < 0:
        raise ValueError(f"{config_prefix}_step_delay must be >= 0")

    if current_degrees is None:
        current_degrees = read_servo_degrees(bus, move_order)

    target_degrees: dict[int, float] = {}
    max_delta = 0.0

    for servo_id in move_order:
        if servo_id not in positions:
            raise ValueError(f"servo id {servo_id} is in move_order but missing from servo_positions")

        initial_degrees, target = positions[servo_id]
        destination = initial_degrees if use_initial_angle else target
        current = current_degrees[servo_id]
        current_degrees[servo_id] = current
        target_degrees[servo_id] = destination
        max_delta = max(max_delta, abs(destination - current))

    if max_delta == 0:
        return

    steps = max(1, math.ceil(max_delta / step_degrees))
    target_name = "initial" if use_initial_angle else "target"

    for step in range(1, steps + 1):
        ratio = step / steps
        for index, servo_id in enumerate(move_order):
            current = current_degrees[servo_id]
            destination = target_degrees[servo_id]
            degrees = current + (destination - current) * ratio
            bus.move_to_raw(servo_id, bus.degrees_to_raw(degrees), time_ms=step_time_ms, speed=speed)

            if move_mode == "sequence" and index < len(move_order) - 1:
                time.sleep(gap_seconds)

        print(f"startup ramp {target_name} step={step}/{steps}")
        time.sleep(step_delay)


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
    config_path = args.config.expanduser().resolve()
    config = read_config(config_path)

    threshold = config.getfloat("display", "threshold")
    poll_interval = config.getfloat("display", "poll_interval")
    blink_delay = 1.0 / max(1, config.getint("display", "blink_fps"))
    full_color = parse_rgb(config.get("display", "full_color"))
    background_color = parse_rgb(config.get("display", "background_color"))
    logger_config = parse_logger_config(config, config_path.parent)

    matrix_zigzag = config.getboolean("matrix", "zigzag")
    matrix_flip_x = config.getboolean("matrix", "flip_x")
    matrix_flip_y = config.getboolean("matrix", "flip_y")
    frames = expression_frames(
        expression_id=config.getint("display", "expression_id"),
        eye_color=parse_rgb(config.get("display", "eye_color")),
        zigzag=matrix_zigzag,
        flip_x=matrix_flip_x,
        flip_y=matrix_flip_y,
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
    servo_move_mode = "together"
    servo_ramp_enabled = False
    servo_ramp_step_degrees = 1.0
    servo_ramp_step_delay = 0.04
    servo_ramp_step_time_ms = 150
    hx = None
    matrix = None

    try:
        if servo_enabled:
            servo_positions = parse_servo_positions(config)
            servo_move_order = parse_int_list(config.get("servo_bus", "move_order"))
            servo_move_time_ms = config.getint("servo_bus", "move_time_ms")
            servo_speed = config.getint("servo_bus", "speed")
            servo_gap_seconds = config.getfloat("servo_bus", "move_gap_seconds")
            servo_move_mode = parse_move_mode(config)
            servo_ramp_enabled = config.getboolean("servo_bus", "ramp_enabled", fallback=False)
            servo_ramp_step_degrees = config.getfloat("servo_bus", "ramp_step_degrees", fallback=1.0)
            servo_ramp_step_delay = config.getfloat("servo_bus", "ramp_step_delay", fallback=0.04)
            servo_ramp_step_time_ms = config.getint("servo_bus", "ramp_step_time_ms", fallback=150)
            startup_position = parse_startup_position(config)
            startup_move_time_ms = config.getint("servo_bus", "startup_move_time_ms", fallback=servo_move_time_ms)
            startup_speed = config.getint("servo_bus", "startup_speed", fallback=servo_speed)
            startup_ramp_enabled = config.getboolean("servo_bus", "startup_ramp_enabled", fallback=False)
            servo_bus = BusServo(
                port=config.get("servo_bus", "port"),
                baud=config.getint("servo_bus", "baud"),
            )
            startup_current_degrees = None
            if startup_position != "none" and startup_ramp_enabled:
                startup_current_degrees = read_servo_degrees(servo_bus, servo_move_order)
                hold_current_servos(servo_bus, startup_current_degrees, servo_move_order)
            if config.getboolean("servo_bus", "enable_torque"):
                for servo_id in servo_move_order:
                    servo_bus.enable_torque(servo_id, True)
            if startup_position != "none":
                if startup_ramp_enabled:
                    ramp_startup_servos(
                        bus=servo_bus,
                        positions=servo_positions,
                        move_order=servo_move_order,
                        use_initial_angle=startup_position == "initial",
                        step_degrees=config.getfloat("servo_bus", "startup_step_degrees"),
                        step_delay=config.getfloat("servo_bus", "startup_step_delay"),
                        step_time_ms=config.getint("servo_bus", "startup_step_time_ms"),
                        speed=startup_speed,
                        gap_seconds=servo_gap_seconds,
                        move_mode=servo_move_mode,
                        current_degrees=startup_current_degrees,
                        config_prefix="servo_bus.startup",
                    )
                else:
                    move_servos(
                        bus=servo_bus,
                        positions=servo_positions,
                        move_order=servo_move_order,
                        use_initial_angle=startup_position == "initial",
                        move_time_ms=startup_move_time_ms,
                        speed=startup_speed,
                        gap_seconds=servo_gap_seconds,
                        move_mode=servo_move_mode,
                    )
                servo_state = startup_position

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
            zigzag=matrix_zigzag,
            flip_x=matrix_flip_x,
            flip_y=matrix_flip_y,
        )

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
                    if servo_ramp_enabled:
                        ramp_startup_servos(
                            bus=servo_bus,
                            positions=servo_positions,
                            move_order=servo_move_order,
                            use_initial_angle=True,
                            step_degrees=servo_ramp_step_degrees,
                            step_delay=servo_ramp_step_delay,
                            step_time_ms=servo_ramp_step_time_ms,
                            speed=servo_speed,
                            gap_seconds=servo_gap_seconds,
                            move_mode=servo_move_mode,
                            config_prefix="servo_bus.ramp",
                        )
                    else:
                        move_servos(
                            bus=servo_bus,
                            positions=servo_positions,
                            move_order=servo_move_order,
                            use_initial_angle=True,
                            move_time_ms=servo_move_time_ms,
                            speed=servo_speed,
                            gap_seconds=servo_gap_seconds,
                            move_mode=servo_move_mode,
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
                if servo_ramp_enabled:
                    ramp_startup_servos(
                        bus=servo_bus,
                        positions=servo_positions,
                        move_order=servo_move_order,
                        use_initial_angle=False,
                        step_degrees=servo_ramp_step_degrees,
                        step_delay=servo_ramp_step_delay,
                        step_time_ms=servo_ramp_step_time_ms,
                        speed=servo_speed,
                        gap_seconds=servo_gap_seconds,
                        move_mode=servo_move_mode,
                        config_prefix="servo_bus.ramp",
                    )
                else:
                    move_servos(
                        bus=servo_bus,
                        positions=servo_positions,
                        move_order=servo_move_order,
                        use_initial_angle=False,
                        move_time_ms=servo_move_time_ms,
                        speed=servo_speed,
                        gap_seconds=servo_gap_seconds,
                        move_mode=servo_move_mode,
                    )
                servo_state = "target"
            time.sleep(blink_delay)

    except KeyboardInterrupt:
        print("Exit")

    finally:
        if matrix is not None:
            matrix.clear()
        if hx is not None:
            hx.cleanup()
        if servo_bus is not None:
            servo_bus.close()


if __name__ == "__main__":
    main()
