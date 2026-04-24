#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from typing import Dict, Iterable, List, Tuple

from rpi_ws281x import Color, PixelStrip

RGB = Tuple[int, int, int]


class EyeMatrix:
    def __init__(
        self,
        width: int = 8,
        height: int = 8,
        pin: int = 12,
        freq_hz: int = 800000,
        dma: int = 10,
        brightness: int = 96,
        invert: bool = False,
        channel: int = 0,
        zigzag: bool = True,
        flip_x: bool = False,
        flip_y: bool = False,
    ):
        self.width = width
        self.height = height
        self.count = width * height
        self.zigzag = zigzag
        self.flip_x = flip_x
        self.flip_y = flip_y

        self.strip = PixelStrip(
            self.count,
            pin,
            freq_hz,
            dma,
            invert,
            brightness,
            channel,
        )
        self.strip.begin()

    def _idx(self, x: int, y: int) -> int:
        if self.flip_x:
            x = self.width - 1 - x
        if self.flip_y:
            y = self.height - 1 - y
        if self.zigzag and (y % 2 == 1):
            x = self.width - 1 - x
        return y * self.width + x

    def clear(self) -> None:
        black = Color(0, 0, 0)
        for i in range(self.count):
            self.strip.setPixelColor(i, black)
        self.strip.show()

    def draw_pixels(self, pixels: Iterable[tuple[int, int, RGB]], background: RGB = (0, 0, 0)) -> None:
        bg = Color(*background)
        for i in range(self.count):
            self.strip.setPixelColor(i, bg)

        for x, y, rgb in pixels:
            if 0 <= x < self.width and 0 <= y < self.height:
                self.strip.setPixelColor(self._idx(x, y), Color(*rgb))

        self.strip.show()


class EyeAnimator:
    def __init__(self, matrix: EyeMatrix, eye_color: RGB = (80, 180, 255), bg_color: RGB = (0, 0, 0)):
        self.matrix = matrix
        self.eye_color = eye_color
        self.bg_color = bg_color

    @staticmethod
    def _mirror(points: Iterable[tuple[int, int]], left_width: int = 3, gap: int = 2) -> List[tuple[int, int]]:
        left = list(points)
        x_offset = left_width + gap
        right = [(x + x_offset, y) for x, y in points]
        return left + right

    def _frame(self, shape: List[tuple[int, int]]) -> List[tuple[int, int, RGB]]:
        return [(x, y, self.eye_color) for x, y in shape]

    def _shapes(self) -> Dict[str, List[List[tuple[int, int]]]]:
        open_eye = self._mirror(
            [
                (0, 2), (1, 1), (2, 2),
                (0, 3), (1, 3), (2, 3),
                (0, 4), (1, 5), (2, 4),
            ]
        )
        narrow_eye = self._mirror([(0, 3), (1, 3), (2, 3)])
        tiny_eye = self._mirror([(1, 3)])
        happy_eye = self._mirror([(0, 4), (1, 3), (2, 4)])
        sad_eye = self._mirror([(0, 2), (1, 3), (2, 2)])
        angry_eye = self._mirror([(0, 2), (1, 2), (2, 3)])

        wink = [(0, 3), (1, 3), (2, 3), (5, 2), (6, 1), (7, 2), (5, 3), (6, 3), (7, 3), (5, 4), (6, 5), (7, 4)]

        return {
            "neutral": [open_eye],
            "happy": [happy_eye],
            "sad": [sad_eye],
            "sleepy": [narrow_eye],
            "surprised": [tiny_eye],
            "angry": [angry_eye],
            "wink": [wink],
            "blink": [open_eye, narrow_eye, [], narrow_eye, open_eye],
        }

    def play(self, state: str, fps: int = 12, loop: bool = True) -> None:
        if state == "demo":
            self._play_demo(fps=fps)
            return

        shapes = self._shapes()
        if state not in shapes:
            raise ValueError(f"Unknown state '{state}'. Available: {', '.join(sorted(shapes))}, demo")

        frames = [self._frame(shape) for shape in shapes[state]]
        delay = 1.0 / max(1, fps)

        try:
            while True:
                for frame in frames:
                    self.matrix.draw_pixels(frame, background=self.bg_color)
                    time.sleep(delay)
                if not loop:
                    break
        finally:
            self.matrix.clear()

    def _play_demo(self, fps: int = 12) -> None:
        sequence = [
            ("neutral", 1.0),
            ("happy", 1.0),
            ("blink", 1.2),
            ("sad", 1.0),
            ("sleepy", 1.0),
            ("surprised", 1.0),
            ("angry", 1.0),
            ("wink", 1.2),
        ]

        shapes = self._shapes()
        delay = 1.0 / max(1, fps)

        try:
            while True:
                for name, seconds in sequence:
                    frames = [self._frame(shape) for shape in shapes[name]]
                    total = max(1, int(seconds * fps))
                    for i in range(total):
                        frame = frames[i % len(frames)]
                        self.matrix.draw_pixels(frame, background=self.bg_color)
                        time.sleep(delay)
        finally:
            self.matrix.clear()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="8x8 eye states on WS281x LED matrix")
    parser.add_argument(
        "--state",
        default="demo",
        choices=["neutral", "happy", "sad", "sleepy", "surprised", "blink", "wink", "angry", "demo"],
    )
    parser.add_argument("--fps", type=int, default=12)
    parser.add_argument("--pin", type=int, default=12)
    parser.add_argument("--brightness", type=int, default=96)
    parser.add_argument("--flip-x", action="store_true")
    parser.add_argument("--flip-y", action="store_true")
    parser.add_argument("--zigzag-off", action="store_true")
    parser.add_argument("--once", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    matrix = EyeMatrix(
        width=8,
        height=8,
        pin=args.pin,
        brightness=max(0, min(255, args.brightness)),
        zigzag=not args.zigzag_off,
        flip_x=args.flip_x,
        flip_y=args.flip_y,
    )
    animator = EyeAnimator(matrix)

    try:
        animator.play(state=args.state, fps=args.fps, loop=not args.once)
    except KeyboardInterrupt:
        matrix.clear()


if __name__ == "__main__":
    main()
