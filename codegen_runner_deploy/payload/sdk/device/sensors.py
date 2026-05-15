"""
device.sensors — 传感器（极简版，只用相机做帧差）

本设备实际硬件只有：相机 + 麦克风 + 扬声器 + 表情点阵。
没有 PIR、温湿度、光感、称重等独立传感器。

接口契约（所有函数失败均返回 None/False，不抛异常）：
    motion_detected() -> bool          帧差分运动检测（用相机帧）
    wait_for_motion(timeout) -> bool   阻塞等待运动，超时返回 False
    cpu_temp() -> float | None         CPU 温度（系统读 /sys/class/thermal）

motion 实现：
    本设备没有 PIR 传感器。motion_detected/wait_for_motion 通过相机拍两帧
    做像素差分。**只能判"有没有东西动"**（便宜、零 LLM），无法判"是不是人"。
    要判"是不是人"用 vision.ask 进一步细判：
        if sensors.motion_detected():
            img = camera.capture()
            info = vision.ask(img, "有人吗？", schema={"has_person": "bool"})
"""
import io
import random
import time as _time

try:
    from PIL import Image, ImageChops, ImageStat
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# ===== 帧差分 motion =====
_prev_frame = None
_MOTION_THRESHOLD = 8.0
_DIFF_SIZE = (160, 120)
_last_motion_ts = 0


def _frame_from_bytes(data: bytes):
    if not _HAS_PIL or not data:
        return None
    try:
        return Image.open(io.BytesIO(data)).convert("RGB").resize(_DIFF_SIZE)
    except Exception as e:
        print(f"[sensors] 解码帧失败: {e}")
        return None


def _motion_by_framediff() -> bool | None:
    global _prev_frame
    from . import camera as _camera
    data = _camera.capture()
    new_frame = _frame_from_bytes(data)
    if new_frame is None:
        return None
    if _prev_frame is None:
        _prev_frame = new_frame
        return False
    diff = ImageChops.difference(new_frame, _prev_frame)
    stat = ImageStat.Stat(diff)
    mean_diff = sum(stat.mean) / len(stat.mean)
    _prev_frame = new_frame
    is_motion = mean_diff > _MOTION_THRESHOLD
    if is_motion:
        print(f"[sensors] motion by framediff (mean={mean_diff:.2f})")
    return is_motion


def motion_detected() -> bool:
    """检测当前画面是否有运动。
      - Pillow 可用 → 帧差分（真实，零 LLM）
      - 否则 fallback mock，约 20% 概率 True（开发机用）
    """
    global _last_motion_ts
    result = _motion_by_framediff()
    if result is not None:
        if result:
            _last_motion_ts = _time.monotonic()
        return result
    now = _time.monotonic()
    if now - _last_motion_ts < 2:
        return True
    if random.random() < 0.2:
        _last_motion_ts = now
        return True
    return False


def wait_for_motion(timeout: float = 30.0, poll_interval: float = 0.5) -> bool:
    """阻塞等待 motion 触发。支持 SIGTERM 中断。"""
    from . import system as _sys
    end = _time.monotonic() + timeout
    while _sys.should_continue() and _time.monotonic() < end:
        if motion_detected():
            return True
        _sys.sleep(poll_interval)
    return False


def cpu_temp() -> float:
    """CPU 温度（摄氏度），真实读 /sys/class/thermal。失败返回 None。"""
    from . import system as _sys
    return _sys.cpu_temp()
