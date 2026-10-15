import os
from pathlib import Path

import httpx
from dotenv import load_dotenv


class ModelError(Exception):
    """模型配置、网络或回复异常，供调用方统一处理。"""


def load_llm_config() -> tuple[str, str, str]:
    # 本文件放在 backend 中，向上一级找到项目根目录的 .env。
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(env_path)

    names = ("LLM_BASE_URL", "LLM_MODEL", "LLM_API_KEY")
    values = tuple((os.getenv(name) or "").strip() for name in names)
    missing = [name for name, value in zip(names, values) if not value]
    if missing:
        raise ModelError("缺少模型配置：" + "、".join(missing))

    base_url, model, api_key = values
    return base_url.rstrip("/"), model, api_key


def chat(messages: list[dict]) -> dict:
    base_url, model, api_key = load_llm_config()

    payload = {
        "model": model,
        "messages": messages,
        "thinking": {"type": "disabled"},
        "max_tokens": 512,
        "stream": False,
    }
    headers = {"Authorization": f"Bearer {api_key}"}

    try:
        with httpx.Client(timeout=httpx.Timeout(60.0, connect=10.0)) as client:
            response = client.post(
                f"{base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
            response.raise_for_status()
    except httpx.TimeoutException:
        raise ModelError("模型请求超时，请稍后重试") from None
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        reasons = {
            401: "模型密钥无效，请检查 LLM_API_KEY",
            402: "模型账户余额不足",
            429: "模型请求过于频繁，请稍后重试",
        }
        raise ModelError(reasons.get(status, f"模型服务返回 HTTP {status}")) from None
    except httpx.RequestError:
        raise ModelError("无法连接模型服务，请检查网络和 LLM_BASE_URL") from None

    try:
        choice = response.json()["choices"][0]
        message = choice["message"]
        finish_reason = choice["finish_reason"]
        content = message["content"]
        valid_message = (
            message.get("role") == "assistant"
            and isinstance(content, str)
            and bool(content.strip())
        )
    except (ValueError, KeyError, IndexError, TypeError, AttributeError):
        raise ModelError("模型返回的数据格式不符合预期") from None

    if finish_reason != "stop":
        raise ModelError("模型未正常完成回复，可能达到输出限制或被服务中断")
    if not valid_message:
        raise ModelError("模型没有返回有效的文字回复")

    return message
