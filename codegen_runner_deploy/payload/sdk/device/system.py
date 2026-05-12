"""
device.system — 生命周期与时间管理

SDK 内部自动注册 SIGTERM/SIGINT handler。生成代码用 should_continue() 做主循环
条件，用 sleep() 替代 time.sleep() — 前者会在收到终止信号时立即返回。
"""
import signal
import sys
import time as _time
from datetime import datetime
from zoneinfo import ZoneInfo

# 我们的目标用户都在北京时区（UTC+8）。SDK 把 `now()` 锁死成北京时间的
# aware datetime，应用代码不用关心 Pi 系统时区是 UTC 还是别的。
_BEIJING_TZ = ZoneInfo("Asia/Shanghai")

_running = True
_exit_callbacks = []


def _handle_signal(sig, frame):
    global _running
    print(f"[system] 收到信号 {sig}，准备优雅退出...")
    _running = False
    for cb in _exit_callbacks:
        try:
            cb()
        except Exception as e:
            print(f"[system] on_exit 回调异常: {e}")


signal.signal(signal.SIGTERM, _handle_signal)
signal.signal(signal.SIGINT, _handle_signal)


def should_continue() -> bool:
    """主循环条件。收到 SIGTERM/SIGINT 后返回 False。

    典型用法：
        while system.should_continue():
            do_work()
            system.sleep(5)
    """
    return _running


def sleep(seconds: float) -> None:
    """可中断 sleep — 收到退出信号时立即返回。

    比 time.sleep 更适合长等待（如 5 秒、60 秒），能让进程及时响应
    SIGTERM。内部以 0.1 秒为粒度检查退出标志。
    """
    end = _time.monotonic() + seconds
    while _running and _time.monotonic() < end:
        _time.sleep(min(0.1, end - _time.monotonic()))


def now() -> datetime:
    """返回**北京时间**（UTC+8）的 aware datetime。

    不管 Pi 系统时区是什么，这个函数永远返回北京时间。生成的代码里写
    `if 6 <= now.hour < 10:` 时直接按北京 6-10 点判断，不用关心时区。
    """
    return datetime.now(_BEIJING_TZ)


def cpu_temp() -> float:
    """读取 CPU 温度（摄氏度）。失败返回 None。"""
    try:
        with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
            return int(f.read().strip()) / 1000.0
    except Exception as e:
        print(f"[system] 读取 CPU 温度失败: {e}")
        return None


def on_exit(callback) -> None:
    """注册退出时执行的回调（收到 SIGTERM/SIGINT 时调用）。

    可多次注册，按注册顺序执行。异常不会中断其他回调。
    """
    _exit_callbacks.append(callback)
