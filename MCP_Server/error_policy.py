"""错误策略与重试包装器。

使用 tenacity 提供指数回退重试策略，并提供一个简单的破坏性操作审批检查点
（生产环境应该替换为更安全的审批流程）。
"""
from __future__ import annotations

import functools
import logging
import os
from typing import Callable, Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


def retry_on_exception(attempts: int = 3, min_wait: int = 1, max_wait: int = 10):
    def decorator(func: Callable[..., Any]):
        @retry(stop=stop_after_attempt(attempts), wait=wait_exponential(min=min_wait, max=max_wait),
               retry=retry_if_exception_type(Exception))
        @functools.wraps(func)
        def wrapped(*args, **kwargs):
            return func(*args, **kwargs)

        return wrapped

    return decorator


def is_destructive_allowed() -> bool:
    """检查环境变量或文件是否允许 agent 执行破坏性操作。

    生产建议：替换为人工审批或集中策略引擎。当前实现使用环境变量 `AGENT_ALLOW_DESTRUCTIVE=1`。
    """
    return os.environ.get("AGENT_ALLOW_DESTRUCTIVE", "0") in ("1", "true", "True")


def require_destructive_approval(func: Callable[..., Any]):
    """装饰器：若破坏性未被允许则抛出 PermissionError。"""

    @functools.wraps(func)
    def wrapped(*args, **kwargs):
        if not is_destructive_allowed():
            logger.warning("Destructive operation blocked by policy: %s", func.__name__)
            raise PermissionError("Destructive operations are disabled by policy")
        return func(*args, **kwargs)

    return wrapped
