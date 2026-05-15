"""
device.net — 网络请求

http_get 使用真 requests 库；weather 返回 mock 数据（真实实现会接 OpenWeatherMap 等）。
接口契约：
    http_get(url, params=None, headers=None) -> dict   返回 JSON，失败返回 None
    weather(city) -> dict                               天气查询
    is_online() -> bool                                 是否联网
"""
import random

try:
    import requests  # noqa
    _has_requests = True
except ImportError:
    _has_requests = False


def http_get(url: str, params: dict = None, headers: dict = None, timeout: float = 10) -> dict:
    """GET 请求，返回解析后的 JSON 字典。失败返回 None。"""
    if not _has_requests:
        print("[net] requests 模块未安装")
        return None
    try:
        import requests
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        try:
            return r.json()
        except ValueError:
            return {"text": r.text, "status_code": r.status_code}
    except Exception as e:
        print(f"[net] http_get 失败 ({url}): {e}")
        return None


def weather(city: str) -> dict:
    """查询城市天气。返回 {city, temp_c, condition, humidity}。失败返回 None。

    Mock 实现：返回合理的假数据，不联网。
    """
    if not city:
        return None
    conditions = ["晴", "多云", "阴", "小雨", "雷阵雨"]
    data = {
        "city": city,
        "temp_c": round(15 + random.uniform(-5, 15), 1),
        "condition": random.choice(conditions),
        "humidity": random.randint(30, 85),
        "wind_kph": random.randint(3, 25),
    }
    print(f"[net] weather({city}): {data}")
    return data


def is_online() -> bool:
    """检查是否联网（ping 一下公共 DNS 即可）。Mock 返回 True。"""
    return True
