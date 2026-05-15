"""
device.camera — 摄像头（拍照 / 录像）

真实硬件实现：
    - capture/capture_to: 调系统命令 rpicam-still 拍 JPEG
    - record_video: rpicam-vid → MP4 (转封装需要 ffmpeg)
真机不可用时（开发机或 rpicam 缺失）回退到 Pillow mock。

接口契约保持不变，调用代码无需感知后端实现。
"""
import os
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

_WIDTH = 640
_HEIGHT = 480
_RPICAM_STILL = shutil.which("rpicam-still") or shutil.which("libcamera-still")
_RPICAM_VID = shutil.which("rpicam-vid") or shutil.which("libcamera-vid")
_FFMPEG = shutil.which("ffmpeg")
_HAS_RPICAM = _RPICAM_STILL is not None

# Pillow fallback 资源
_ASSETS_DIR = os.path.join(os.path.dirname(__file__), "_assets")
_PLACEHOLDER_PATH = os.path.join(_ASSETS_DIR, "placeholder.jpg")
try:
    from PIL import Image, ImageDraw, ImageFont
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False


def _capture_with_rpicam() -> bytes:
    """用 rpicam-still 拍一张照片并读回 bytes。"""
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as tf:
        tmp_path = tf.name
    try:
        cmd = [
            _RPICAM_STILL,
            "--nopreview",
            "--width", str(_WIDTH),
            "--height", str(_HEIGHT),
            "-o", tmp_path,
        ]
        # rpicam-still 默认 5 秒预览给 AEC/AWB 收敛，daemon 不能等这么久。
        # 实测 -t 300 太短 AEC 来不及收敛 → 容易过曝；500ms 已足够清晰。
        cmd += ["-t", "500"]
        subprocess.run(cmd, check=True, timeout=15, capture_output=True)
        with open(tmp_path, "rb") as f:
            return f.read()
    finally:
        try: os.unlink(tmp_path)
        except OSError: pass


def _capture_with_pil() -> bytes:
    """开发机 fallback：Pillow 合成或读 placeholder。"""
    if _HAS_PIL:
        import io, random
        bg = (random.randint(30, 80), random.randint(30, 80), random.randint(60, 120))
        img = Image.new("RGB", (_WIDTH, _HEIGHT), bg)
        draw = ImageDraw.Draw(img)
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
        except Exception:
            font = ImageFont.load_default()
        draw.text((20, 20), "MOCK CAMERA", fill="white", font=font)
        draw.text((20, 60), ts, fill="white", font=font)
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return buf.getvalue()
    # 最后兜底
    with open(_PLACEHOLDER_PATH, "rb") as f:
        return f.read()


def capture() -> bytes:
    """拍摄一张照片，返回 JPEG 二进制。失败返回 None。

    优先用 rpicam-still（真机）；不可用时 fallback 到 Pillow mock。
    """
    img = None
    try:
        if _HAS_RPICAM:
            img = _capture_with_rpicam()
        else:
            img = _capture_with_pil()
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode(errors="replace") if e.stderr else ""
        print(f"[camera] rpicam-still 失败: {stderr[:200]}")
        img = _capture_with_pil()
    except Exception as e:
        print(f"[camera] 拍照失败: {e}")
        img = None
    from . import _tracer
    _tracer.log(
        op="camera.capture",
        output={"size_bytes": len(img) if img else 0, "ok": bool(img)},
        image_bytes=img,
    )
    return img


def capture_to(path: str) -> bool:
    """拍照并直接保存到指定路径。成功返回 True。

    真机 rpicam-still 直接 -o 写入，零 bytes 复制。
    """
    ok = False
    size = 0
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if _HAS_RPICAM:
            cmd = [
                _RPICAM_STILL,
                "--nopreview",
                "--width", str(_WIDTH),
                "--height", str(_HEIGHT),
                "-t", "300",
                "-o", path,
            ]
            subprocess.run(cmd, check=True, timeout=15, capture_output=True)
            size = os.path.getsize(path) if os.path.exists(path) else 0
            print(f"[camera] 已保存照片: {path} ({size} bytes)")
            ok = size > 0
        else:
            data = _capture_with_pil()
            with open(path, "wb") as f:
                f.write(data)
            size = len(data)
            print(f"[camera] 已保存照片(mock): {path} ({size} bytes)")
            ok = True
    except subprocess.CalledProcessError as e:
        print(f"[camera] rpicam 调用失败: {e.stderr.decode(errors='replace')[:200] if e.stderr else e}")
        ok = False
    except Exception as e:
        print(f"[camera] 保存失败: {e}")
        ok = False
    # 埋点：把刚保存的图片读回来上报（仅成功时）
    img_for_log = None
    if ok and os.path.exists(path):
        try:
            with open(path, "rb") as f:
                img_for_log = f.read()
        except Exception:
            pass
    from . import _tracer
    _tracer.log(
        op="camera.capture_to",
        input={"path": path},
        output={"ok": ok, "size_bytes": size},
        image_bytes=img_for_log,
    )
    return ok


def record_video(seconds: float, path: str) -> bool:
    """录制视频到文件 (.mp4 或 .h264)。成功返回 True。

    真机用 rpicam-vid 录 H.264，再用 ffmpeg 转封装为 MP4（如果输出 .mp4）。
    路径后缀决定输出格式。
    """
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        suffix = Path(path).suffix.lower()

        if not _HAS_RPICAM:
            # fallback: 写一段元数据占位（保持 mock 行为）
            from . import system as _sys
            _sys.sleep(seconds)
            with open(path, "wb") as f:
                f.write(f"MOCK_VIDEO duration={seconds}s timestamp={datetime.now().isoformat()}\n".encode())
            print(f"[camera] 已录制视频(mock): {path} ({seconds}s)")
            return True

        duration_ms = int(seconds * 1000)
        if suffix == ".h264":
            cmd = [_RPICAM_VID, "--nopreview", "-t", str(duration_ms),
                   "--codec", "h264", "-o", path]
            subprocess.run(cmd, check=True, timeout=int(seconds + 30), capture_output=True)
            print(f"[camera] 已录制视频: {path}")
            return True

        if suffix == ".mp4":
            if _FFMPEG is None:
                print("[camera] ffmpeg 不可用，无法转 MP4，请改用 .h264 后缀")
                return False
            tmp_h264 = path + ".tmp.h264"
            try:
                cmd = [_RPICAM_VID, "--nopreview", "-t", str(duration_ms),
                       "--codec", "h264", "-o", tmp_h264]
                subprocess.run(cmd, check=True, timeout=int(seconds + 30), capture_output=True)
                cmd2 = [_FFMPEG, "-y", "-i", tmp_h264, "-c", "copy", path]
                subprocess.run(cmd2, check=True, timeout=30, capture_output=True)
                print(f"[camera] 已录制视频: {path}")
                return True
            finally:
                try: os.unlink(tmp_h264)
                except OSError: pass

        print(f"[camera] 不支持的视频后缀: {suffix}（仅 .mp4/.h264）")
        return False
    except Exception as e:
        print(f"[camera] 录像失败: {e}")
        return False
