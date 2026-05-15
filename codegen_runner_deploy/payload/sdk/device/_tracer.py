"""device._tracer — SDK 埋点上报

每次 SDK 调用（camera.capture / vision.ask / speaker.say / ai.chat / face.set_emotion / mic.record）
都会通过 tracer.log(...) 把操作元信息 + 输入输出 + 可选图片字节 fire-and-forget 发到
backend POST /api/codegen/device/event。Workshop UI 拉时间线展示。

设计目标：
- 不阻塞主流程（log 立即返回；后台线程发 HTTP）
- env 不全（local dev / 没部署）安全降级（什么都不做）
- 失败不抛 — 用户的代码不能因为我们埋点跪
"""
import json
import os
import threading
import time

try:
    import requests
except ImportError:
    requests = None


def _read_env():
    return {
        "server_url": os.environ.get("CODEGEN_SERVER_URL", "").rstrip("/"),
        "device_id": os.environ.get("DEVICE_ID", ""),
        "device_secret": os.environ.get("DEVICE_SECRET", ""),
        "hw_token": os.environ.get("HARDWARE_TOKEN", ""),
        "task_id": os.environ.get("TASK_ID", ""),
        "attempt": int(os.environ.get("CODEGEN_ATTEMPT", "1") or 1),
    }


_ENV = _read_env()
# 跟踪未完成线程，flush() 等它们结束（测试用）
_inflight: list[threading.Thread] = []
_inflight_lock = threading.Lock()


def is_enabled() -> bool:
    """env 是否齐全到能上报"""
    return bool(
        _ENV["server_url"]
        and _ENV["device_id"]
        and _ENV["device_secret"]
        and _ENV["task_id"]
        and requests is not None
    )


def _post(payload: dict, attachment_bytes: bytes | None,
          attachment_mime: str = "application/octet-stream") -> None:
    """同步 HTTP 发送。供测试 patch 替换。"""
    if requests is None:
        return
    url = f"{_ENV['server_url']}/api/codegen/device/event"
    headers = {"Authorization": _ENV["hw_token"]}
    try:
        if attachment_bytes:
            ext = {"image/jpeg": "jpg", "image/png": "png",
                   "audio/wav": "wav", "audio/mpeg": "mp3"}.get(attachment_mime, "bin")
            requests.post(
                url,
                headers=headers,
                data={"json": json.dumps(payload, ensure_ascii=False)},
                files={"attachment": (f"a.{ext}", attachment_bytes, attachment_mime)},
                timeout=15,
            )
        else:
            requests.post(url, headers=headers, json=payload, timeout=10)
    except Exception:
        # 用户主代码不能因为埋点失败而崩
        pass


def _spawn(payload: dict, attachment_bytes: bytes | None,
           attachment_mime: str = "application/octet-stream") -> None:
    t = threading.Thread(target=_post,
                         args=(payload, attachment_bytes, attachment_mime),
                         daemon=True)
    with _inflight_lock:
        _inflight.append(t)
    t.start()


def log(op: str, *, input: dict | None = None, output: dict | None = None,
        attachment_bytes: bytes | None = None,
        attachment_mime: str = "application/octet-stream",
        # 兼容老 image_bytes 参数名
        image_bytes: bytes | None = None,
        duration_ms: int | None = None) -> None:
    """埋点。fire-and-forget，立即返回。"""
    if not is_enabled():
        return
    if attachment_bytes is None and image_bytes is not None:
        attachment_bytes = image_bytes
        attachment_mime = "image/jpeg"
    payload = {
        "device_id": _ENV["device_id"],
        "device_secret": _ENV["device_secret"],
        "task_id": _ENV["task_id"],
        "attempt": _ENV["attempt"],
        "op": op,
    }
    if input is not None:
        payload["input"] = input
    if output is not None:
        payload["output"] = output
    if duration_ms is not None:
        payload["duration_ms"] = duration_ms
    _spawn(payload, attachment_bytes, attachment_mime)


def flush(timeout: float = 5.0) -> None:
    """等所有 inflight 线程结束。测试用。"""
    deadline = time.time() + timeout
    while True:
        with _inflight_lock:
            alive = [t for t in _inflight if t.is_alive()]
            _inflight[:] = alive
            if not alive:
                return
        if time.time() > deadline:
            return
        time.sleep(0.01)
