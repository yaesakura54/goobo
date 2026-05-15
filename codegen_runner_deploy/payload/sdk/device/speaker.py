"""
device.speaker — 扬声器（播放音频 / TTS）

play(path|bytes)  真机用 paplay/aplay 子进程播放 WAV；不可用时打印 mock
say(text)         TTS — 调后端 /api/codegen/device/tts 拿 WAV 字节再 play()
stop()            停止当前播放（kill 子进程）

实现说明：
    早期版本用 sounddevice + sd.play() + sd.wait()，长跑 daemon 里反复调用会
    累积 PortAudio 内部 stream 状态，遇到 PulseAudio underrun/recover 时
    主线程 futex 死锁，或 stream.write 被节流导致音频被静默吞掉。
    改成 subprocess 到 paplay（PulseAudio 原生）/ aplay（ALSA 原生）后：
        · 每次播放是独立进程，没有累积状态
        · 播完进程退出，资源彻底释放
        · stop() 直接 kill 子进程，立即打断
        · subprocess.run(timeout=...) 比 sd.wait() 可靠
"""
import io
import os
import shutil
import subprocess
import tempfile
import threading
import wave

# 选播放器：优先 paplay（PulseAudio 原生），降级 aplay（直 ALSA）
_PLAYER = None
for _bin in ("paplay", "aplay"):
    if shutil.which(_bin):
        _PLAYER = _bin
        break
_HAS_PLAYER = _PLAYER is not None

# 当前播放子进程（stop() 用）
_proc: subprocess.Popen | None = None
_proc_lock = threading.Lock()


# paplay/aplay 播完会自己退出，timeout 仅作"卡死时兜底"用，给一个固定的大值就够
_PLAY_TIMEOUT_SEC = 120


def play(path_or_bytes, blocking: bool = True) -> bool:
    """播放音频文件或 WAV bytes。返回 True 表示播放成功（或开始播放）。

    Args:
        path_or_bytes: WAV 文件路径 或 WAV bytes
        blocking: 默认阻塞到播完；False 则后台异步播放
    """
    # 拿到 wav bytes
    if isinstance(path_or_bytes, bytes):
        wav_bytes = path_or_bytes
        label = f"bytes ({len(wav_bytes)})"
    elif isinstance(path_or_bytes, str):
        if not os.path.exists(path_or_bytes):
            print(f"[speaker] 音频文件不存在: {path_or_bytes}")
            return False
        with open(path_or_bytes, "rb") as f:
            wav_bytes = f.read()
        label = f"{path_or_bytes} ({len(wav_bytes)} bytes)"
    else:
        print(f"[speaker] 不支持的输入类型: {type(path_or_bytes)}")
        return False

    if not _HAS_PLAYER:
        print(f"[speaker] (mock) 播放 {label}")
        return True

    # 写到临时 WAV 让 paplay/aplay 读
    tmp_path = None
    import time as _time
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            tmp_path = f.name

        cmd = [_PLAYER, tmp_path]
        # 诊断日志：cmd / 退出码 / 实际耗时 / paplay 的 stderr
        _DBG = open("/tmp/speaker_debug.log", "ab")
        _DBG.write(f"\n[{_time.strftime('%H:%M:%S')}] play: {label}\n".encode())
        _DBG.write(f"  cmd: {cmd}\n".encode())
        _DBG.flush()

        global _proc
        t0 = _time.time()
        if blocking:
            with _proc_lock:
                _proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=_DBG)
            try:
                rc = _proc.wait(timeout=_PLAY_TIMEOUT_SEC)
            except subprocess.TimeoutExpired:
                _proc.kill(); _proc.wait()
                _DBG.write(b"  -> timeout\n"); _DBG.close()
                print(f"[speaker] 播放超时（{_PLAY_TIMEOUT_SEC}s），已 kill")
                return False
            finally:
                with _proc_lock:
                    _proc = None
            elapsed = _time.time() - t0
            _DBG.write(f"  -> rc={rc} elapsed={elapsed:.2f}s\n".encode())
            _DBG.close()
        else:
            with _proc_lock:
                _proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=_DBG)
        print(f"[speaker] 已播放 {label} (player={_PLAYER})")
        return True
    except Exception as e:
        print(f"[speaker] 播放失败: {e}")
        return False
    finally:
        if tmp_path and os.path.exists(tmp_path):
            try: os.unlink(tmp_path)
            except Exception: pass


def say(text: str, voice: str = "female", speed: float = 1.0,
        blocking: bool = True) -> bool:
    """TTS 朗读一段文字。

    内部走后端 /api/codegen/device/tts → 火山引擎 TTS → 拿到 WAV → 调 play() 播放。
    后端不可达或 sounddevice 不可用时降级为 print，不会让代码崩。
    """
    from . import _tracer
    log_input = {"text": text, "voice": voice, "speed": speed}

    if not text:
        _tracer.log(op="speaker.say", input=log_input,
                    output={"ok": False, "reason": "empty text"})
        return False

    # 调后端 TTS
    from . import _llm
    if _llm.is_available():
        import base64
        import requests
        try:
            r = requests.post(
                f"{_llm.SERVER_URL}/api/codegen/device/tts",
                json={
                    "device_id": _llm.DEVICE_ID,
                    "device_secret": _llm.DEVICE_SECRET,
                    "text": text,
                    "voice": voice,
                    "speed": speed,
                },
                headers={"Authorization": _llm.HW_TOKEN},
                timeout=30,
            )
            if r.status_code == 200:
                data = r.json().get("data") or {}
                wav_b64 = data.get("wav_b64")
                if wav_b64:
                    wav_bytes = base64.b64decode(wav_b64)
                    print(f"[speaker] TTS 朗读({voice}, speed={speed}): {text[:40]}")
                    # 上报：把 WAV 字节也带上，UI 可播放
                    _tracer.log(
                        op="speaker.say",
                        input=log_input,
                        output={"ok": True, "wav_size_bytes": len(wav_bytes)},
                        attachment_bytes=wav_bytes,
                        attachment_mime="audio/wav",
                    )
                    return play(wav_bytes, blocking=blocking)
            else:
                err = r.json().get("error", r.text[:100]) if r.text else "?"
                print(f"[speaker] TTS HTTP {r.status_code}: {err}")
                _tracer.log(op="speaker.say", input=log_input,
                            output={"ok": False, "http_status": r.status_code, "err": err})
                return False
        except Exception as e:
            print(f"[speaker] TTS 调用异常: {e}")
            _tracer.log(op="speaker.say", input=log_input,
                        output={"ok": False, "exception": str(e)})
            return False

    # Fallback：纯打印
    print(f"[speaker] (mock TTS, 后端不可达) 朗读({voice}): {text}")
    _tracer.log(op="speaker.say", input=log_input,
                output={"ok": True, "mock": True})
    return True


def stop() -> None:
    """停止当前播放（kill 子进程）。"""
    global _proc
    with _proc_lock:
        if _proc is not None and _proc.poll() is None:
            try:
                _proc.kill()
                _proc.wait(timeout=2)
            except Exception:
                pass
        _proc = None
    print("[speaker] 停止播放")
