"""
device.vision — 计算机视觉（接入多模态 LLM 的自由接口）

Mock: 随机返回假结果。真实实现会把图片 + prompt + schema 发给多模态模型
（GPT-4V / Claude Vision / Qwen-VL 等），由它分析并按 schema 格式返回。

核心接口（推荐）：
    ask(image_bytes, prompt, schema=None) -> str | dict
        自由提问。schema 为空返回文字，指定 schema 返回结构化字典。

便捷封装（基于 ask 的常见场景）：
    detect_faces(image_bytes) -> list[dict]
    detect_person(image_bytes) -> bool
    recognize_text(image_bytes) -> str
"""
import random


# ================= 核心接口 =================

def ask(image_bytes: bytes, prompt: str, schema: dict = None,
        model: str = None, temperature: float = 0.5, max_tokens: int = 1024):
    """向多模态视觉模型提问。

    Args:
        image_bytes: 图片二进制（通常来自 camera.capture()）
        prompt: 自然语言问题或指令
        schema: 可选；若提供则返回符合 schema 的字典。
        model: 可选，默认 doubao-seed-1-6-flash-250615（原生支持图文，快且便宜）
        temperature: 默认 0.5（视觉任务偏确定性）
        max_tokens: 最大输出 token

    Returns:
        不传 schema  -> str (自然语言回答)
        传 schema    -> dict (按 schema 的键返回)

    Examples:
        answer = vision.ask(img, "画面里发生什么？")
        info = vision.ask(img, "分析画面", schema={
            "person_count": "int",
            "has_danger": "bool",
            "description": "str, 简短场景描述",
        })
    """
    from . import _llm
    from . import _tracer

    log_input = {"prompt": prompt, "schema": schema, "image_size_bytes": len(image_bytes) if image_bytes else 0}

    if not image_bytes:
        print("[vision] ask: 输入图片为空")
        out = {} if schema else ""
        _tracer.log(op="vision.ask", input=log_input, output={"result": out})
        return out

    prompt_preview = (prompt or "")[:60]

    # 真实 LLM（多模态）
    if _llm.is_available():
        result = _llm.call_llm(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            image_bytes=image_bytes,
            response_schema=schema,
        )
        if result is not None:
            content = result.get("content")
            used_model = result.get("model", "doubao")
            usage = result.get("usage", {})
            tag = "schema" if schema else "text"
            print(f"[vision] ask[{tag}] model={used_model} tokens={usage.get('total_tokens', 0)} prompt={prompt_preview!r}")
            if content is not None:
                _tracer.log(op="vision.ask",
                            input=log_input,
                            output={"result": content, "model": used_model,
                                    "tokens": usage.get("total_tokens", 0)},
                            image_bytes=image_bytes)
                return content

    # Fallback 到 mock
    if schema is None:
        text = _mock_text_response(prompt)
        print(f"[vision] ask[mock]({prompt_preview!r}) -> {text}")
        _tracer.log(op="vision.ask", input=log_input,
                    output={"result": text, "mock": True}, image_bytes=image_bytes)
        return text
    result = _mock_structured_response(prompt, schema)
    print(f"[vision] ask[mock, schema]({prompt_preview!r}) -> {result}")
    _tracer.log(op="vision.ask", input=log_input,
                output={"result": result, "mock": True}, image_bytes=image_bytes)
    return result


# ================= 便捷封装 =================

def detect_faces(image_bytes: bytes) -> list:
    """检测人脸，返回人脸框列表。每项 {"x","y","w","h","confidence"}。"""
    if not image_bytes:
        print("[vision] detect_faces: 输入为空")
        return []
    if random.random() < 0.5:
        n = random.choice([1, 1, 2])
        faces = []
        for _ in range(n):
            faces.append({
                "x": random.randint(50, 400),
                "y": random.randint(50, 300),
                "w": random.randint(80, 150),
                "h": random.randint(80, 150),
                "confidence": round(random.uniform(0.7, 0.98), 2),
            })
        print(f"[vision] 检测到 {len(faces)} 张人脸")
        return faces
    print("[vision] 未检测到人脸")
    return []


def detect_person(image_bytes: bytes) -> bool:
    """是否有人。Mock 30% True。"""
    if not image_bytes:
        return False
    result = random.random() < 0.3
    print(f"[vision] detect_person: {result}")
    return result


def recognize_text(image_bytes: bytes) -> str:
    """OCR。Mock 从候选列表随机选。"""
    if not image_bytes:
        return ""
    samples = ["Hello World", "谷语工坊", "MOCK OCR TEXT", "123-456-789"]
    text = random.choice(samples)
    print(f"[vision] OCR: {text}")
    return text


# ================= Mock 内部实现 =================

_MOCK_SCENE_TEMPLATES = [
    "画面里有一个人，似乎在看着镜头微笑。背景是室内环境，光线柔和。",
    "这是一个空荡的房间，桌上摆着几本书和一盏台灯。",
    "照片中能看到两个人正在交谈，神情放松。",
    "画面显示的是一张桌面，上面有键盘和显示屏。",
    "没有明显的人物主体，画面整体色调偏暖。",
]


def _mock_text_response(prompt: str) -> str:
    """根据 prompt 关键词挑一个合理的 mock 文本。"""
    lower = (prompt or "").lower()
    if any(k in prompt for k in ["笑话", "搞笑", "逗"]):
        return "我看到你了，给你讲个笑话：为什么数学书很悲伤？因为它充满了问题。"
    if any(k in prompt for k in ["危险", "安全", "问题"]):
        return "画面里没有明显的危险物品，整体看起来很安全。"
    if any(k in prompt for k in ["做什么", "在干", "发生"]):
        return "画面里有人，看起来在做日常活动，没有异常。"
    return random.choice(_MOCK_SCENE_TEMPLATES)


def _mock_value_for_type(hint: str):
    """根据 schema 值的类型描述返回 mock 数据。"""
    h = str(hint).lower()
    if "int" in h or "整数" in h or "数量" in h or "count" in h:
        return random.randint(0, 3)
    if "float" in h or "浮点" in h:
        return round(random.uniform(0, 1), 2)
    if "bool" in h or "布尔" in h or "是否" in h:
        return random.choice([True, False])
    if "list" in h or "列表" in h or "数组" in h:
        return random.choice([["book", "cup", "lamp"], ["person"], []])
    # 默认字符串
    return random.choice([
        "未检测到特殊内容",
        "看起来一切正常",
        "画面清晰，无异常",
    ])


def _mock_structured_response(prompt: str, schema: dict) -> dict:
    """按 schema 字段生成 mock 值。"""
    if not isinstance(schema, dict):
        return {}
    return {key: _mock_value_for_type(hint) for key, hint in schema.items()}
