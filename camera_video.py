# camera_video.py
# -*- coding: utf-8 -*-

import argparse
import subprocess
from pathlib import Path
from datetime import datetime


def run_cmd(cmd):
    print("Running:")
    print(" ".join(str(x) for x in cmd))
    subprocess.run(cmd, check=True)


def record_h264(temp_h264, seconds, width=None, height=None, framerate=None, bitrate=None):
    duration_ms = int(seconds * 1000)

    cmd = [
        "rpicam-vid",
        "--nopreview",
        "-t", str(duration_ms),
        "--codec", "h264",
        "-o", str(temp_h264),
    ]

    if width is not None:
        cmd += ["--width", str(width)]

    if height is not None:
        cmd += ["--height", str(height)]

    if framerate is not None:
        cmd += ["--framerate", str(framerate)]

    if bitrate is not None:
        cmd += ["--bitrate", str(bitrate)]

    run_cmd(cmd)


def h264_to_mp4(input_h264, output_mp4, framerate=None):
    cmd = [
        "ffmpeg",
        "-y",
    ]

    # 对裸 H.264，有些播放器/ffmpeg 版本可能需要明确帧率
    if framerate is not None:
        cmd += ["-r", str(framerate)]

    cmd += [
        "-i", str(input_h264),
        "-c", "copy",
        str(output_mp4),
    ]

    run_cmd(cmd)


def record_video(
    output=None,
    seconds=10,
    width=None,
    height=None,
    framerate=None,
    bitrate=None,
    keep_h264=False,
):
    if output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"video_{ts}.mp4"

    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    suffix = output_path.suffix.lower()

    if suffix == ".h264":
        record_h264(
            temp_h264=output_path,
            seconds=seconds,
            width=width,
            height=height,
            framerate=framerate,
            bitrate=bitrate,
        )
        print(f"Saved H.264 video: {output_path}")
        return

    if suffix != ".mp4":
        raise ValueError("Output file must end with .mp4 or .h264")

    temp_h264 = output_path.with_suffix(".tmp.h264")

    try:
        record_h264(
            temp_h264=temp_h264,
            seconds=seconds,
            width=width,
            height=height,
            framerate=framerate,
            bitrate=bitrate,
        )

        h264_to_mp4(
            input_h264=temp_h264,
            output_mp4=output_path,
            framerate=framerate,
        )

        print(f"Saved MP4 video: {output_path}")

    finally:
        if temp_h264.exists() and not keep_h264:
            temp_h264.unlink()


def main():
    parser = argparse.ArgumentParser(description="Record video using Raspberry Pi CSI camera.")
    parser.add_argument("-o", "--output", default=None, help="Output path, e.g. ~/test.mp4 or ~/test.h264")
    parser.add_argument("-t", "--seconds", type=float, default=10, help="Recording duration in seconds")
    parser.add_argument("--width", type=int, default=None, help="Video width")
    parser.add_argument("--height", type=int, default=None, help="Video height")
    parser.add_argument("--framerate", type=int, default=None, help="Frame rate, e.g. 30")
    parser.add_argument("--bitrate", type=int, default=None, help="Bitrate, e.g. 4000000")
    parser.add_argument("--keep-h264", action="store_true", help="Keep intermediate .h264 file")

    args = parser.parse_args()

    record_video(
        output=args.output,
        seconds=args.seconds,
        width=args.width,
        height=args.height,
        framerate=args.framerate,
        bitrate=args.bitrate,
        keep_h264=args.keep_h264,
    )


if __name__ == "__main__":
    main()