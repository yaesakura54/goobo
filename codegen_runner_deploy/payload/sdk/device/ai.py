"""
device.ai — AI 对话与语音处理

Mock: 返回固定/随机响应。真实实现会路由到后端 chat / ASR 服务。
接口契约：
    transcribe(audio_bytes) -> str                          语音转文字
    chat(prompt, context=None, schema=None) -> str | dict   LLM 对话，可要求结构化输出
    synthesize_speech(text) -> bytes                        TTS 合成 WAV bytes
"""
import random


_MOCK_TRANSCRIBES = [
    "你好小谷",
    "今天天气怎么样",
    "给我讲个笑话",
    "帮我设个闹钟",
    "我有点无聊",
]

_MOCK_REPLIES = [
    "好的主人，我在这里。",
    "嗯，让我想想...",
    "这个问题很有意思！",
    "收到，正在处理。",
]


def transcribe(audio_bytes: bytes) -> str:
    """语音转文字。输入 WAV bytes（推荐 16kHz/单声道/16bit），返回识别文本。

    内部走后端 /api/codegen/device/asr → 火山豆包 Sauce 大模型 ASR。
    后端不可达时降级为 mock，不会让代码崩。
    """
    from . import _tracer
    audio_size = len(audio_bytes) if audio_bytes else 0
    if not audio_bytes:
        print("[ai] transcribe: 输入为空")
        _tracer.log(op="ai.transcribe",
                    input={"audio_size_bytes": 0},
                    output={"text": ""})
        return ""

    from . import _llm
    if _llm.is_available():
        import base64
        import requests
        try:
            r = requests.post(
                f"{_llm.SERVER_URL}/api/codegen/device/asr",
                json={
                    "device_id": _llm.DEVICE_ID,
                    "device_secret": _llm.DEVICE_SECRET,
                    "audio_b64": base64.b64encode(audio_bytes).decode("ascii"),
                },
                headers={"Authorization": _llm.HW_TOKEN},
                timeout=60,
            )
            if r.status_code == 200:
                text = (r.json().get("data") or {}).get("text", "")
                print(f"[ai] transcribe: {text!r}")
                _tracer.log(op="ai.transcribe",
                            input={"audio_size_bytes": audio_size},
                            output={"text": text or ""})
                return text or ""
            err = (r.json().get("error", "") if r.text else "")
            print(f"[ai] transcribe HTTP {r.status_code}: {err}")
        except Exception as e:
            print(f"[ai] transcribe 异常: {e}")

    # Fallback mock
    text = random.choice(_MOCK_TRANSCRIBES)
    _tracer.log(op="ai.transcribe",
                input={"audio_size_bytes": audio_size},
                output={"text": text, "mock": True})
    print(f"[ai] transcribe[mock]: {text}")
    return text


def chat(prompt: str, context: list = None, schema: dict = None,
         model: str = None, temperature: float = 0.7, max_tokens: int = 1024):
    """与 AI 对话。支持自由文本或结构化输出。

    Args:
        prompt: 用户消息 / 指令
        context: 可选历史对话（格式: [{"role": "user/assistant", "content": "..."}]）
        schema: 可选；传了就要求 LLM 按 schema 字段返回字典
                格式: {字段名: 类型说明("int"/"str"/"bool"/"list"/自然语言)}
        model: 可选，默认 doubao-seed-1-6-flash-250615（快、便宜）
               其他可选："doubao-seed-2-0-lite-260215"（通用）
                         "doubao-seed-2-0-pro-260215"（高质量）
        temperature: 0.0 - 2.0，越高越发散
        max_tokens: 最大输出 token 数

    Returns:
        不传 schema -> str
        传 schema   -> dict

    Examples:
        # 普通对话
        reply = ai.chat("讲个笑话")

        # 结构化决策（推荐：让 LLM 做判断并返回字典）
        plan = ai.chat("用户说'早上好'，决定设备响应", schema={
            "greeting": "str, 回应语",
            "should_play_music": "bool",
            "mood_score": "int, 1-5",
        })
        speaker.say(plan["greeting"])
    """
    from . import _llm
    from . import _tracer

    log_input = {"prompt": prompt, "schema": schema, "temperature": temperature}

    if not prompt and not context:
        out = {} if schema else ""
        _tracer.log(op="ai.chat", input=log_input, output={"result": out})
        return out

    # 真实 LLM
    if _llm.is_available():
        messages = list(context) if context else []
        if prompt:
            messages.append({"role": "user", "content": prompt})
        result = _llm.call_llm(
            messages=messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            response_schema=schema,
        )
        if result is not None:
            content = result.get("content")
            used_model = result.get("model", "doubao")
            usage = result.get("usage", {})
            tag = "schema" if schema else "text"
            print(f"[ai] chat[{tag}] model={used_model} tokens={usage.get('total_tokens', 0)}")
            if content is not None:
                _tracer.log(op="ai.chat",
                            input=log_input,
                            output={"result": content, "model": used_model,
                                    "tokens": usage.get("total_tokens", 0)})
                return content

    # Fallback 到 mock
    if schema is None:
        reply = random.choice(_MOCK_REPLIES)
        print(f"[ai] chat[mock] {prompt[:40]!r} -> {reply}")
        _tracer.log(op="ai.chat", input=log_input, output={"result": reply, "mock": True})
        return reply
    result = _mock_structured_reply(prompt, schema)
    print(f"[ai] chat[mock, schema] {prompt[:40]!r} -> {result}")
    _tracer.log(op="ai.chat", input=log_input, output={"result": result, "mock": True})
    return result


def _mock_structured_reply(prompt: str, schema: dict) -> dict:
    """按 schema 字段类型生成 mock 值，语义参考 vision._mock_value_for_type。"""
    if not isinstance(schema, dict):
        return {}
    out = {}
    for key, hint in schema.items():
        h = str(hint).lower()
        if "int" in h or "整数" in h or "数量" in h:
            out[key] = random.randint(0, 5)
        elif "float" in h or "浮点" in h:
            out[key] = round(random.uniform(0, 1), 2)
        elif "bool" in h or "布尔" in h or "是否" in h:
            out[key] = random.choice([True, False])
        elif "list" in h or "列表" in h:
            out[key] = ["item1", "item2"]
        else:
            out[key] = random.choice(_MOCK_REPLIES)
    return out


def synthesize_speech(text: str, voice: str = "female") -> bytes:
    """TTS 合成。返回 WAV bytes。Mock: 返回空 WAV 占位。"""
    import io
    import struct
    import wave
    if not text:
        return None
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(struct.pack("<" + "h" * 1600, *([0] * 1600)))
    data = buf.getvalue()
    print(f"[ai] synthesize_speech({voice}): '{text[:30]}...' -> {len(data)} bytes")
    return data
