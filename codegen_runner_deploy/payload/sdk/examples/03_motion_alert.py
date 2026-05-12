"""示例 03: 运动告警 — sensors + camera + face + speaker。

检测到运动时：拍照存档 + 切换"惊讶"表情 + TTS 朗读告警，2 秒后回到 neutral。
"""
from device import system, sensors, camera, face, speaker, storage


def main():
    print("运动检测告警启动")
    face.set_emotion("neutral")
    storage.save_text("startup.txt", str(system.now()))

    while system.should_continue():
        if sensors.wait_for_motion(timeout=10):
            ts = int(system.now().timestamp())
            path = storage.output_path(f"intruder_{ts}.jpg")
            camera.capture_to(path)
            face.set_emotion("surprised")
            speaker.say("有人来了哦", voice="female")
            print(f"抓拍保存: {path}")
            system.sleep(3)
            face.set_emotion("neutral")
    print("运动检测已退出")


if __name__ == "__main__":
    main()
