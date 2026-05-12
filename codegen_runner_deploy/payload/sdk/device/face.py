"""
device.face — 8x8 表情点阵（小谷的"眼睛"）

硬件：8x8 WS281x LED 矩阵，goobo/eye_matrix_test/eye_matrix_8x8.py 提供驱动。
本设备**没有屏幕**，所有视觉反馈通过这个表情点阵。

可用表情（8 个）：
    neutral    平静（默认睁眼）
    happy      开心（眯眯眼）
    sad        难过（下垂眼）
    sleepy     困倦（窄眼）
    surprised  惊讶（小眼）
    angry      生气（皱眼）
    wink       眨左眼
    blink      眨眼动画（睁→窄→闭→窄→睁）

接口契约（保持稳定，将来真机/mock 切换无感）：
    set_emotion(state) -> bool         设为常态表情，非阻塞，后台保持
    blink() -> bool                    播一次眨眼动画后回到上次的常态表情
    wink() -> bool                     单眼眨
    off() -> None                      熄灭点阵
    current() -> str                   返回当前表情名

实现策略：
    真机 — 用 subprocess 启动 eye_matrix_8x8.py --state X 后台播；
           切换时杀旧进程换新。
    Mock — 仅 print；保持当前 emotion 状态在 _state 里。
"""
import os
import shutil
import signal
import subprocess
import threading
import time

# 可用的表情列表（必须和 eye_matrix_8x8.py 的 _shapes() 一致）
EMOTIONS = ("neutral", "happy", "sad", "sleepy", "surprised", "angry", "wink", "blink")

# 真机 EyeMatrix 脚本路径（goobo 部署到 Pi 的位置）
# 默认用当前用户 home 下的相对路径，兼容 neurobo / guyu 等不同用户
_EYE_MATRIX_SCRIPT = os.environ.get(
    "DEVICE_EYE_MATRIX_SCRIPT",
    os.path.expanduser("~/test/goobo/eye_matrix_test/eye_matrix_8x8.py"),
)
_HAS_HW = os.path.exists(_EYE_MATRIX_SCRIPT)

# 当前状态
_state = {"emotion": "neutral", "brightness": 80}
_proc: subprocess.Popen | None = None
_lock = threading.Lock()


def _kill_proc():
    """终止后台 eye_matrix 子进程。"""
    global _proc
    if _proc is None:
        return
    if _proc.poll() is None:
        try:
            _proc.send_signal(signal.SIGTERM)
            _proc.wait(timeout=2)
        except subprocess.TimeoutExpired:
            try: _proc.kill()
            except Exception: pass
    _proc = None


def _spawn(state: str, brightness: int, loop: bool = True):
    """启动 eye_matrix 后台子进程播指定表情。"""
    global _proc
    cmd = [
        "sudo", "-n", "python3", _EYE_MATRIX_SCRIPT,
        "--state", state,
        "--brightness", str(brightness),
    ]
    if not loop:
        cmd.append("--once")
    try:
        _proc = subprocess.Popen(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError as e:
        print(f"[face] 启动 eye_matrix 失败: {e}")
        _proc = None


def set_emotion(state: str, brightness: int = 80) -> bool:
    """切换到指定表情（非阻塞，后台保持）。

    Args:
        state: 必须是 EMOTIONS 中的一个
        brightness: 1-255，亮度
    Returns:
        True 表示设置成功（mock 或真实）；False 表示参数错误
    """
    from . import _tracer
    if state not in EMOTIONS:
        print(f"[face] 不支持的表情 {state!r}，可选: {EMOTIONS}")
        _tracer.log(op="face.set_emotion",
                    input={"state": state, "brightness": brightness},
                    output={"ok": False, "reason": "invalid state"})
        return False
    with _lock:
        _state["emotion"] = state
        _state["brightness"] = max(1, min(255, brightness))
        if _HAS_HW:
            _kill_proc()
            _spawn(state, _state["brightness"], loop=True)
            print(f"[face] (real) emotion={state} brightness={_state['brightness']}")
        else:
            print(f"[face] (mock) emotion={state}")
    _tracer.log(op="face.set_emotion",
                input={"state": state, "brightness": brightness},
                output={"ok": True})
    return True


def blink() -> bool:
    """播一次眨眼动画（约 0.4s），结束后恢复 set_emotion 之前的表情。"""
    prev = _state["emotion"]
    if not set_emotion("blink"):
        return False
    time.sleep(0.5)  # 约一个 blink 周期
    return set_emotion(prev)


def wink() -> bool:
    """眨一次左眼（短暂的 wink 表情后恢复）。"""
    prev = _state["emotion"]
    if not set_emotion("wink"):
        return False
    time.sleep(0.6)
    return set_emotion(prev)


def _clear_pixels() -> None:
    """让 eye_matrix 跑一次 brightness=0 --once 自然退出，触发其 finally: matrix.clear()。

    WS281x 像素带寄存器，SIGTERM 直接杀循环进程后像素状态会**保留**最后一帧，
    肉眼看就是"灯没灭"。eye_matrix_8x8.py 的 play() 在 finally 里有 matrix.clear()，
    所以让它正常退出一次才是真熄灯。
    """
    cmd = [
        "sudo", "-n", "python3", _EYE_MATRIX_SCRIPT,
        "--state", "neutral",
        "--brightness", "0",
        "--once",
    ]
    try:
        subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except Exception as e:
        print(f"[face] 清屏失败: {e}")


def off() -> None:
    """熄灭点阵。"""
    with _lock:
        _state["emotion"] = "off"
        if _HAS_HW:
            _kill_proc()
            _clear_pixels()
        print("[face] 熄灭")


def current() -> str:
    """返回当前表情名。"""
    return _state["emotion"]


# 进程退出时清理
def _cleanup_at_exit():
    if _HAS_HW:
        _kill_proc()
        _clear_pixels()


# 注册到系统 SDK 的退出回调
try:
    from . import system as _sys
    _sys.on_exit(_cleanup_at_exit)
except Exception:
    pass
