"""
Cheat Engine AI Agent 的 LLM (Large Language Model) 模块。

这包括用于通过 Ollama 与本地 LLM 交互的类和函数，
包括提示生成和响应处理。
"""
from .client import OllamaClient

__all__ = ['OllamaClient']