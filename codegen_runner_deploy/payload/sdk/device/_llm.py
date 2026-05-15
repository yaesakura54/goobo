"""
device._llm — 统一的后端 LLM 调用入口（ai / vision 内部共用）

通过 POST {SERVER}/api/codegen/device/llm 调 backend，让 backend 调 Doubao。
必需环境变量：
    CODEGEN_SERVER_URL  (后端地址)
    DEVICE_ID
    DEVICE_SECRET
    HARDWARE_TOKEN
失败时返回 None，由上层决定回退到 mock 还是报错。
"""
import base64
import json
import os

try:
    import requests
    _HAS_REQUESTS = True
except ImportError:
    _HAS_REQUESTS = False


SERVER_URL = os.environ.get("CODEGEN_SERVER_URL", "").rstrip("/")
DEVICE_ID = os.environ.get("DEVICE_ID", "")
DEVICE_SECRET = os.environ.get("DEVICE_SECRET", "")
HW_TOKEN = os.environ.get("HARDWARE_TOKEN", "")

DEFAULT_MODEL = "doubao-seed-1-6-flash-250615"

_auth_ready = bool(SERVER_URL and DEVICE_ID and DEVICE_SECRET and HW_TOKEN and _HAS_REQUESTS)


def is_available() -> bool:
    return _auth_ready


def call_llm(
    *,
    prompt: str = None,
    messages: list = None,
    model: str = None,
    temperature: float = 0.7,
    max_tokens: int = 1024,
    image_bytes: bytes = None,
    images_bytes: list = None,
    response_schema: dict = None,
    timeout: float = 60.0,
):
    """统一 LLM 调用。返回字典 {"content": ..., "usage": ..., "model": ...} 或 None。

    - prompt / messages 二选一（prompt 更简单）
    - image_bytes / images_bytes 自动 base64；有图会走 flash 视觉模型
    - response_schema 传了就返回 content 是 dict；否则 str
    """
    if not _auth_ready:
        return None

    imgs_b64 = []
    if image_bytes:
        imgs_b64.append(base64.b64encode(image_bytes).decode("ascii"))
    if images_bytes:
        for b in images_bytes:
            if b:
                imgs_b64.append(base64.b64encode(b).decode("ascii"))

    body = {
        "device_id": DEVICE_ID,
        "device_secret": DEVICE_SECRET,
        "model": model or DEFAULT_MODEL,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if prompt is not None:
        body["prompt"] = prompt
    if messages is not None:
        body["messages"] = messages
    if imgs_b64:
        body["images_b64"] = imgs_b64
    if response_schema is not None:
        body["response_schema"] = response_schema

    try:
        r = requests.post(
            f"{SERVER_URL}/api/codegen/device/llm",
            json=body,
            headers={"Authorization": HW_TOKEN, "Content-Type": "application/json"},
            timeout=timeout,
        )
        if r.status_code != 200:
            print(f"[_llm] 调用失败 http={r.status_code} body={r.text[:200]}")
            return None
        data = r.json().get("data") or {}
        return data
    except Exception as e:
        print(f"[_llm] 调用异常: {e}")
        return None
