#!/usr/bin/env python3
from __future__ import annotations

import argparse
import configparser
import sys
import time
from pathlib import Path
from typing import Iterable, Tuple

BASE_DIR = Path(__file__).resolve().parent
GOOBO_DIR = BASE_DIR.parent

# Reuse the sibling hardware test modules without copying their code here.
sys.path.insert(0, str(GOOBO_DIR / "hx711_test"))
sys.path.insert(0, str(GOOBO_DIR / "eye_matrix_test"))

from eye_matrix_8x8 import EyeMatrix  # noqa: E402
from hx711 import HX711  # noqa: E402

RGB = Tuple[int, int, int]


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
        (2, 1), (3, 1), (4, 1), (5, 1),
        (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2),
        (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3),
        (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4),
        (1, 5), (2, 5), (3, 5), (4, 5), (5, 5), (6, 5),
        (2, 6), (3, 6), (4, 6), (5, 6),
    ]
    narrow_eye = [(1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3)]
    half_open_eye = [
        (1, 2), (2, 2), (3, 2), (4, 2), (5, 2), (6, 2),
        (1, 3), (2, 3), (3, 3), (4, 3), (5, 3), (6, 3),
        (1, 4), (2, 4), (3, 4), (4, 4), (5, 4), (6, 4),
    ]
    return [open_eye, half_open_eye, narrow_eye, [], narrow_eye, half_open_eye, open_eye]


def blink_frames(eye_color: RGB, eye_count: int) -> list[list[tuple[int, int, RGB]]]:
    if eye_count == 1:
        shapes = single_eye_shapes()
    elif eye_count == 2:
        shapes = double_eye_shapes()
    else:
        raise ValueError("display.eye_count must be 1 or 2")

    return [[(x, y, eye_color) for x, y in shape] for shape in shapes]


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
    frames = blink_frames(
        eye_color=parse_rgb(config.get("display", "eye_color")),
        eye_count=config.getint("display", "eye_count"),
    )
    frame_index = 0
    mode = None

    try:
        print("Keep the scale empty, tare start...")
        hx.tare(times=config.getint("hx711", "tare_times"))
        hx.set_scale(config.getfloat("hx711", "scale"))
        print(f"offset={hx.offset:.2f}, threshold={threshold:.3f}")

        while True:
            weight = hx.get_weight(times=config.getint("hx711", "read_times"))
            print(f"weight={weight:8.3f}")

            if weight > threshold:
                if mode != "full":
                    matrix.draw_pixels([], background=full_color)
                    mode = "full"
                time.sleep(poll_interval)
                continue

            mode = "blink"
            matrix.draw_pixels(frames[frame_index % len(frames)], background=background_color)
            frame_index += 1
            time.sleep(blink_delay)

    except KeyboardInterrupt:
        print("Exit")

    finally:
        matrix.clear()
        hx.cleanup()


if __name__ == "__main__":
    main()
