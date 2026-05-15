"""
device.storage — 输出文件管理

非 mock：真实写文件到 /opt/device-app/output/。生成代码禁止直接写其他目录。
接口契约：
    output_path(name) -> str        规范化的输出路径
    save_bytes(name, data)          保存二进制
    save_text(name, text)           保存文本
    append_line(name, line)         追加一行（CSV / 日志常用）
    read_text(name) -> str          读文本
    exists(name) -> bool            判断输出文件是否存在
"""
import os

# 真机默认 /opt/device-app/output；开发机/容器可用 DEVICE_OUTPUT_DIR 覆盖
OUTPUT_DIR = os.environ.get("DEVICE_OUTPUT_DIR", "/opt/device-app/output")


def _ensure_dir():
    os.makedirs(OUTPUT_DIR, exist_ok=True)


def output_path(name: str) -> str:
    """返回 /opt/device-app/output/<name> 的绝对路径，并确保目录存在。"""
    _ensure_dir()
    # 防御：禁止相对路径穿越
    safe = os.path.basename(name) if "/" not in name else name.lstrip("/")
    return os.path.join(OUTPUT_DIR, safe)


def save_bytes(name: str, data: bytes) -> str:
    """保存二进制数据。返回实际写入的路径。"""
    path = output_path(name)
    with open(path, "wb") as f:
        f.write(data)
    print(f"[storage] 已保存 {len(data)} bytes -> {path}")
    return path


def save_text(name: str, text: str) -> str:
    """保存文本。返回实际写入的路径。"""
    path = output_path(name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"[storage] 已保存文本 -> {path}")
    return path


def append_line(name: str, line: str) -> str:
    """追加一行（自动补 \\n）。返回实际写入的路径。

    用于 CSV / 日志文件的增量写入。调用者负责格式（包括 CSV 表头）。
    """
    path = output_path(name)
    with open(path, "a", encoding="utf-8") as f:
        if not line.endswith("\n"):
            line = line + "\n"
        f.write(line)
    return path


def read_text(name: str) -> str:
    """读取文本文件。不存在返回空字符串。"""
    path = output_path(name)
    if not os.path.exists(path):
        return ""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def exists(name: str) -> bool:
    """检查输出文件是否存在。"""
    return os.path.exists(output_path(name))
