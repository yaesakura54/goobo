# mic_record.py
# -*- coding: utf-8 -*-

import argparse
import wave
from pathlib import Path

import sounddevice as sd


def list_devices():
    print(sd.query_devices())


def record_wav(output: str, seconds: float, samplerate: int, channels: int, device: int | None):
    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("Available audio devices:")
    print(sd.query_devices())

    print(f"\nRecording {seconds} seconds...")
    print(f"samplerate={samplerate}, channels={channels}, device={device}")

    frames = int(seconds * samplerate)

    audio = sd.rec(
        frames,
        samplerate=samplerate,
        channels=channels,
        dtype="int16",
        device=device,
    )
    sd.wait()

    with wave.open(str(output_path), "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(2)  # int16 = 2 bytes
        wf.setframerate(samplerate)
        wf.writeframes(audio.tobytes())

    print(f"Saved WAV: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Record audio from microphone to WAV.")
    parser.add_argument("-o", "--output", default="mic_test.wav", help="Output WAV path")
    parser.add_argument("-t", "--seconds", type=float, default=5.0, help="Recording duration")
    parser.add_argument("-r", "--samplerate", type=int, default=16000, help="Sample rate")
    parser.add_argument("-c", "--channels", type=int, default=1, help="Number of channels")
    parser.add_argument("--device", type=int, default=None, help="Input device ID from device list")
    parser.add_argument("--list-devices", action="store_true", help="Only list audio devices")
    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    record_wav(args.output, args.seconds, args.samplerate, args.channels, args.device)


if __name__ == "__main__":
    main()