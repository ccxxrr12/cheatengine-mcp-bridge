"""Result parsers and pydantic models for CE bridge outputs.

包含针对 Cheat Engine 返回的通用解析器与少量模型，便于 LangChain agent 对结果进行断言与结构化处理。
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, ValidationError

logger = logging.getLogger(__name__)


class GenericCEResult(BaseModel):
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


def parse_generic_ce_result(raw: Any) -> GenericCEResult:
    """将原始返回（可能是 dict 或 JSON 字符串）解析为 GenericCEResult。

    若解析失败，会抛出 ValidationError 或 ValueError。
    """
    if isinstance(raw, str):
        try:
            raw_obj = json.loads(raw)
        except Exception as e:
            logger.exception("Failed to json-decode raw string result")
            raise ValueError("Invalid JSON string returned from CE") from e
    elif isinstance(raw, dict):
        raw_obj = raw
    else:
        # 直接包装为失败结构
        raise ValueError("Unsupported result type")

    try:
        return GenericCEResult.parse_obj(raw_obj)
    except ValidationError as e:
        logger.debug("Validation error parsing CE result: %s", e)
        # 尝试 best-effort map
        mapped = {
            "success": bool(raw_obj.get("success", False)),
            "result": raw_obj.get("result") or raw_obj,
            "error": raw_obj.get("error") or None,
        }
        return GenericCEResult.parse_obj(mapped)
