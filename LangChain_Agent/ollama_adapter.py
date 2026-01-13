"""Ollama HTTP adapter.

提供一个小型、可测试的 Ollama 客户端，用于在生产环境下与本地/远端 Ollama 服务通信。
要求：Ollama server 可通过 HTTP API 提供 /api/generate 接口（常见本地部署）。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class OllamaClient:
    def __init__(self, base_url: str = "settings.OLLAMA_URL", model: str = "settings.OLLAMA_MODEL", timeout: int = 60):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, prompt: str, max_tokens: int = 512, temperature: float = 0.0) -> Dict[str, Any]:
        """向 Ollama 请求生成文本。返回解析后的 dict：{text, raw}。

        注意：不同 Ollama 部署返回字段可能不同，函数尝试兼容常见变体。
        """
        url = f"{self.base_url}/api/generate"
        payload = {"model": self.model, "prompt": prompt, "max_tokens": max_tokens, "temperature": temperature}

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
            resp.raise_for_status()
        except Exception as e:
            logger.exception("Ollama request failed")
            raise

        # 尝试解析 JSON 负载；若不是 JSON 则返回原始文本
        try:
            data = resp.json()
        except Exception:
            text = resp.text
            return {"text": text, "raw": resp.text}

        # 常见字段抽取
        text = None
        for key in ("text", "output", "response", "result"):
            if key in data:
                text = data[key]
                break

        # 兼容某些返回嵌套结构
        if text is None:
            # 搜索第一个字符串值
            def find_str(v):
                if isinstance(v, str):
                    return v
                if isinstance(v, dict):
                    for vv in v.values():
                        r = find_str(vv)
                        if r:
                            return r
                if isinstance(v, list) and v:
                    return find_str(v[0])
                return None

            text = find_str(data) or ""

        return {"text": text, "raw": data}

    @staticmethod
    def extract_tool_call(text: str) -> Optional[Dict[str, Any]]:
        """从 LLM 文本中提取工具调用 JSON（如果存在）。

        约定：LLM 应在输出中以 JSON 块返回工具调用，例如:
        ```\n+        {"tool_call": {"name": "read_memory", "args": {"address":"0x123"}}}\n+        ```
        """
        if not text:
            return None
        # 尝试在文本中查找第一个 JSON 对象
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None
        try:
            fragment = text[start:end + 1]
            data = json.loads(fragment)
            if "tool_call" in data:
                return data["tool_call"]
            return data
        except Exception:
            return None
