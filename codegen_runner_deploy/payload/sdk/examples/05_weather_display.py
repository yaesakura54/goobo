"""示例 05: 天气播报 — net + face + speaker（没有屏幕，用表情 + 语音表达）。

每 30 分钟查询一次上海天气，根据天气切表情 + 朗读出来。
"""
from device import system, net, face, speaker


def emotion_for_weather(condition: str) -> str:
    """根据天气情况挑表情"""
    if condition in ("晴",):
        return "happy"
    if condition in ("阴", "多云"):
        return "neutral"
    if condition in ("小雨", "雷阵雨", "大雨"):
        return "sad"
    return "neutral"


def main():
    print("天气播报启动")
    while system.should_continue():
        data = net.weather("上海")
        if data:
            emotion = emotion_for_weather(data["condition"])
            face.set_emotion(emotion)
            text = (
                f"上海当前 {data['condition']}，气温 {data['temp_c']} 度，"
                f"湿度 {data['humidity']}%"
            )
            speaker.say(text, voice="female")
            print(f"已播报: {text} (face={emotion})")
        system.sleep(1800)  # 30 分钟刷新一次
    print("天气播报已退出")


if __name__ == "__main__":
    main()
