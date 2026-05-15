"""示例 04: 语音对话 — 麦克风 + ASR + Chat + TTS。

录音 3 秒 → 转文字 → 调 AI 对话 → 朗读回复。
"""
from device import system, mic, ai, speaker


def main():
    print("语音对话程序启动")
    round_num = 0
    while system.should_continue():
        round_num += 1
        print(f"第 {round_num} 轮对话，开始录音...")
        audio = mic.record(seconds=3)
        if not audio:
            system.sleep(2)
            continue

        user_text = ai.transcribe(audio)
        print(f"用户说: {user_text}")

        reply = ai.chat(user_text)
        print(f"小谷回复: {reply}")

        speaker.say(reply)
        system.sleep(2)
    print("对话程序已退出")


if __name__ == "__main__":
    main()
