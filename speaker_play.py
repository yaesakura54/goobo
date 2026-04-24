# speaker_play.py
# -*- coding: utf-8 -*-

import argparse
import math
import wave
from pathlib import Path

import numpy as np
import sounddevice as sd


def list_devices():
    print(sd.query_devices())


def play_tone(freq: float, seconds: float, samplerate: int, volume: float, device: int | None):
    print("Available audio devices:")
    print(sd.query_devices())

    print(f"\nPlaying tone: {freq} Hz, {seconds} seconds, volume={volume}, device={device}")

    t = np.linspace(0, seconds, int(seconds * samplerate), endpoint=False)
    audio = volume * np.sin(2 * math.pi * freq * t)

    sd.play(audio, samplerate=samplerate, device=device)
    sd.wait()

    print("Done.")


def play_wav(path: str, device: int | None):
    wav_path = Path(path).expanduser().resolve()

    if not wav_path.exists():
        raise FileNotFoundError(f"File not found: {wav_path}")

    with wave.open(str(wav_path), "rb") as wf:
        channels = wf.getnchannels()
        samplerate = wf.getframerate()
        sampwidth = wf.getsampwidth()
        frames = wf.getnframes()
        raw = wf.readframes(frames)

    if sampwidth != 2:
        raise ValueError("This simple player only supports 16-bit PCM WAV.")

    audio = np.frombuffer(raw, dtype=np.int16)

    if channels > 1:
        audio = audio.reshape(-1, channels)

    print(f"Playing WAV: {wav_path}")
    print(f"samplerate={samplerate}, channels={channels}, frames={frames}, device={device}")

    sd.play(audio, samplerate=samplerate, device=device)
    sd.wait()

    print("Done.")


def main():
    parser = argparse.ArgumentParser(description="Play speaker test tone or WAV file.")
    parser.add_argument("--list-devices", action="store_true", help="Only list audio devices")

    parser.add_argument("--wav", default=None, help="Path to WAV file to play")
    parser.add_argument("--freq", type=float, default=440.0, help="Tone frequency")
    parser.add_argument("-t", "--seconds", type=float, default=2.0, help="Tone duration")
    parser.add_argument("-r", "--samplerate", type=int, default=44100, help="Sample rate")
    parser.add_argument("--volume", type=float, default=0.3, help="Volume, 0.0 - 1.0")
    parser.add_argument("--device", type=int, default=None, help="Output device ID from device list")

    args = parser.parse_args()

    if args.list_devices:
        list_devices()
        return

    if args.wav:
        play_wav(args.wav, args.device)
    else:
        play_tone(args.freq, args.seconds, args.samplerate, args.volume, args.device)


if __name__ == "__main__":
    main()