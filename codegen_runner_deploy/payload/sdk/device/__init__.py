"""
谷语工坊设备 SDK (device)

为树莓派设备提供统一的硬件抽象层。生成的代码应只通过本 SDK 操作硬件，
不要直接 import cv2 / picamera2 / RPi.GPIO 等底层库。

当前为 mock 实现：camera/mic/sensors 返回模拟数据，speaker/display/led
打印到 stdout。真实硬件到位后替换实现，接口契约保持不变。

使用方式：
    from device import system, camera, storage, sensors
    # 或直接：
    import device

典型模式：
    from device import system, storage, camera

    def main():
        print("程序启动")
        while system.should_continue():
            path = storage.output_path(f"shot_{int(system.now().timestamp())}.jpg")
            camera.capture_to(path)
            print(f"已保存: {path}")
            system.sleep(5)
        print("程序已优雅退出")

    if __name__ == "__main__":
        main()
"""

__version__ = "0.1.0-mock"

from . import (
    system,
    camera,
    mic,
    speaker,
    face,
    sensors,
    storage,
    vision,
    ai,
    net,
)

__all__ = [
    "system",
    "camera",
    "mic",
    "speaker",
    "face",
    "sensors",
    "storage",
    "vision",
    "ai",
    "net",
]
