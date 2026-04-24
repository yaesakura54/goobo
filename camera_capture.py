# camera_capture.py
# -*- coding: utf-8 -*-

import argparse
import subprocess
from pathlib import Path
from datetime import datetime


def capture_image(output: str | None = None, width: int | None = None, height: int | None = None):
    if output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"camera_{ts}.jpg"

    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "rpicam-still",
        "--nopreview",
        "-o",
        str(output_path),
    ]

    if width is not None:
        cmd += ["--width", str(width)]
    if height is not None:
        cmd += ["--height", str(height)]

    print("Running:", " ".join(cmd))
    subprocess.run(cmd, check=True)

    print(f"Saved image: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Capture one image using Raspberry Pi CSI camera.")
    parser.add_argument("-o", "--output", default=None, help="Output image path, e.g. ~/test.jpg")
    parser.add_argument("--width", type=int, default=None, help="Image width")
    parser.add_argument("--height", type=int, default=None, help="Image height")
    args = parser.parse_args()

    capture_image(args.output, args.width, args.height)


if __name__ == "__main__":
    main()