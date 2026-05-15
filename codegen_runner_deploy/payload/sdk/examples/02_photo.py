"""示例 02: 定时拍照 — 摄像头 + 存储。

每 5 秒拍一张照片保存。
"""
from device import system, camera, storage


def main():
    print("定时拍照程序启动")
    count = 0
    while system.should_continue():
        ts = int(system.now().timestamp())
        path = storage.output_path(f"photo_{ts}.jpg")
        if camera.capture_to(path):
            count += 1
            print(f"已拍摄 {count} 张，最新: {path}")
        system.sleep(5)
    print(f"拍照程序已退出，共 {count} 张")


if __name__ == "__main__":
    main()
