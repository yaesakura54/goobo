"""
device.mic — 麦克风录音

真实硬件实现：sounddevice + numpy 录 WAV。
不可用时（开发机/Pi 没装 sounddevice）回退到生成静音 WAV。
"""
import io
import os
import struct
import wave

_SAMPLE_RATE = 16000
_SAMPLE_WIDTH = 2  # 16-bit
_CHANNELS = 1

try:
    import sounddevice as _sd
    import numpy as _np
    _HAS_SD = True
except ImportError:
    _HAS_SD = False


def _record_with_sounddevice(seconds: float) -> bytes:
    """真机录音：sounddevice + 默认输入设备 → WAV bytes。"""
    frames = int(seconds * _SAMPLE_RATE)
    audio = _sd.rec(
        frames,
        samplerate=_SAMPLE_RATE,
        channels=_CHANNELS,
        dtype="int16",
    )
    _sd.wait()  # 阻塞直到录完

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPLE_WIDTH)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(audio.tobytes())
    return buf.getvalue()


def _record_silence(seconds: float) -> bytes:
    """fallback：合成静音 WAV。"""
    from . import system as _sys
    _sys.sleep(seconds)
    n_frames = int(_SAMPLE_RATE * seconds)
    silence = struct.pack("<" + "h" * n_frames, *([0] * n_frames))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(_CHANNELS)
        wf.setsampwidth(_SAMPLE_WIDTH)
        wf.setframerate(_SAMPLE_RATE)
        wf.writeframes(silence)
    return buf.getvalue()


def record(seconds: float) -> bytes:
    """录音指定秒数，返回 WAV 二进制。失败返回 None。"""
    data = None
    try:
        if _HAS_SD:
            data = _record_with_sounddevice(seconds)
            print(f"[mic] 真实录音 {seconds}s ({len(data)} bytes)")
        else:
            data = _record_silence(seconds)
            print(f"[mic] 静音 mock 录音 {seconds}s ({len(data)} bytes) — sounddevice 未安装")
    except Exception as e:
        print(f"[mic] 录音失败 (fallback 到静音): {e}")
        try:
            data = _record_silence(seconds)
        except Exception:
            data = None
    from . import _tracer
    _tracer.log(
        op="mic.record",
        input={"seconds": seconds},
        output={"size_bytes": len(data) if data else 0, "ok": bool(data)},
    )
    return data


def record_to(seconds: float, path: str) -> bool:
    """录音并直接保存到 WAV 文件。成功返回 True。"""
    data = record(seconds)
    ok = False
    if data is not None:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "wb") as f:
                f.write(data)
            print(f"[mic] 已保存录音: {path}")
            ok = True
        except Exception as e:
            print(f"[mic] 保存失败: {e}")
            ok = False
    from . import _tracer
    _tracer.log(
        op="mic.record_to",
        input={"seconds": seconds, "path": path},
        output={"ok": ok},
    )
    return ok
