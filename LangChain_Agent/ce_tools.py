"""Cheat Engine tool wrappers for agent usage.

这些 wrapper 直接调用现有的 `CEBridgeClient` 实例 (`mcp_cheatengine.ce_client`) 并返回解析好的结果。
工具分为只读与破坏性，破坏性操作受 `error_policy` 的保护。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Callable, Dict, List

from .result_parsers import parse_generic_ce_result
from .error_policy import retry_on_exception, require_destructive_approval

logger = logging.getLogger(__name__)

# 导入 ce_client
from ..MCP_Server.mcp_cheatengine import ce_client  # when running from MCP_Server working dir



def ensure_client():
    if ce_client is None:
        raise RuntimeError("ce_client not available; ensure mcp_cheatengine is importable and named pipe available")


@retry_on_exception(attempts=3)
def ping() -> Dict[str, Any]:
    ensure_client()
    raw = ce_client.send_command("ping")
    return parse_generic_ce_result(raw).dict()


@retry_on_exception(attempts=3)
def evaluate_lua(code: str) -> Dict[str, Any]:
    ensure_client()
    raw = ce_client.send_command("evaluate_lua", {"code": code})
    return parse_generic_ce_result(raw).dict()


@retry_on_exception(attempts=3)
def read_memory(address: str, size: int = 256) -> Dict[str, Any]:
    ensure_client()
    raw = ce_client.send_command("read_memory", {"address": address, "size": size})
    return parse_generic_ce_result(raw).dict()


@retry_on_exception(attempts=3)
def read_string(address: str, max_length: int = 256, wide: bool = False) -> Dict[str, Any]:
    ensure_client()
    raw = ce_client.send_command("read_string", {"address": address, "max_length": max_length, "wide": wide})
    return parse_generic_ce_result(raw).dict()


@require_destructive_approval
@retry_on_exception(attempts=2)
def auto_assemble(script: str) -> Dict[str, Any]:
    ensure_client()
    raw = ce_client.send_command("auto_assemble", {"script": script})
    return parse_generic_ce_result(raw).dict()


def build_tool_metadata() -> List[Dict[str, Any]]:
    """返回工具元数据列表，便于 agent 在注册工具时使用。

    元数据示例: {name, func, description, destructive: bool}
    """
    return [
        {"name": "ping", "func": ping, "description": "Check connectivity and CE version", "destructive": False},
        {"name": "evaluate_lua", "func": evaluate_lua, "description": "Execute Lua code in Cheat Engine (returns output as JSON)", "destructive": False},
        {"name": "read_memory", "func": read_memory, "description": "Read raw bytes from memory at address", "destructive": False},
        {"name": "read_string", "func": read_string, "description": "Read string from memory", "destructive": False},
        {"name": "auto_assemble", "func": auto_assemble, "description": "Run AutoAssembler script (destructive). Requires approval.", "destructive": True},
    ]


def make_langchain_tools() -> List[Any]:
    """如果安装了 langchain，返回可直接注册给 `initialize_agent` 的工具对象。

    兼容性说明：不同 langchain 版本的工具 API 可能不同；此函数尝试优雅退化为简单 dict 列表。
    """
    try:
        from langchain.tools import Tool

        tools = []
        for meta in build_tool_metadata():
            # Tool 接受一个 call 函数，要求字符串 -> 字符串。我们封装为 JSON in/out
            def make_call(f):
                def call_tool(text_input: str) -> str:
                    try:
                        # 期望 agent 将参数以 JSON 字符串传入
                        args = json.loads(text_input) if text_input else {}
                    except Exception:
                        args = {"input": text_input}
                    res = f(**args) if isinstance(args, dict) else f(args)
                    return json.dumps(res, ensure_ascii=False)

                return call_tool

            tools.append(Tool(name=meta["name"], func=make_call(meta["func"]), description=meta["description"]))
        return tools
    except Exception:
        # 回退：返回简单可调用字典，供自定义 agent 使用
        return build_tool_metadata()
