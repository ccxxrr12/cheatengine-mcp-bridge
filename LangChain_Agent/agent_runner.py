"""Agent runner for Prean C (agent as controller).

此模块启动 LangChain agent（若可用）并将 Cheat Engine 工具注册为工具库。
设计目标：生产就绪的最小控制器，包含审计日志、dry-run、破坏性审批检查与重试策略。
"""
from __future__ import annotations

import json
import logging
import os
from typing import Any, Dict, List

from dotenv import load_dotenv

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.tools import Tool
from langchain_community.agents import create_tool_calling_agent
from langchain.agents import AgentExecutor
from langchain_community.chat_models import ChatOllama

from .ollama_adapter import OllamaClient
from .ce_tools import make_langchain_tools, build_tool_metadata

load_dotenv()

LOG_LEVEL = os.environ.get("AGENT_LOG_LEVEL", "INFO")
logging.basicConfig(level=LOG_LEVEL)
logger = logging.getLogger("mcp_agent")


class OllamaLLMWrapper:
    """简单的 LangChain LLM 适配器（尽可能兼容不同版本）。

    在有 langchain 的环境下可以作为自定义 LLM 传入 agent。
    """

    def __init__(self, client: OllamaClient, max_tokens: int = 512, temperature: float = 0.0):
        self.client = client
        self.max_tokens = max_tokens
        self.temperature = temperature

    def generate_text(self, prompt: str) -> str:
        resp = self.client.generate(prompt, max_tokens=self.max_tokens, temperature=self.temperature)
        return resp.get("text", "")


def run_with_langchain(prompt: str, ollama: OllamaClient, tools: List[Any], steps: int = 6) -> None:
    try:
        # 创建ChatOllama实例
        llm = ChatOllama(
            base_url=ollama.base_url,
            model=ollama.model,
            temperature=0.0
        )

        # 创建提示模板
        prompt_template = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant that can use tools to analyze memory, disassemble code, and manage breakpoints in Cheat Engine context. Use the available tools when needed."),
            ("human", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])

        # 创建工具调用代理
        agent = create_tool_calling_agent(
            llm=llm,
            tools=tools,
            prompt=prompt_template
        )

        # 创建代理执行器
        agent_executor = AgentExecutor(
            agent=agent,
            tools=tools,
            verbose=True,
            max_iterations=steps,
            early_stopping_method="force"
        )

        logger.info("Starting agent (LangChain) for prompt: %s", prompt)
        result = agent_executor.invoke({"input": prompt})
        logger.info("Agent finished. Result:\n%s", result)
    except Exception as e:
        logger.exception("LangChain integration failed, falling back to direct loop: %s", e)
        run_fallback_loop(prompt, ollama, tools, steps)


def run_fallback_loop(prompt: str, ollama: OllamaClient, tools_meta: List[Dict[str, Any]], max_steps: int = 6) -> None:
    """当没有 langchain 或集成失败时使用的回退调度器。

    协议约定：OLLAMA 输出应包含可解析的工具调用 JSON（见 ollama_adapter.extract_tool_call）。
    """
    logger.info("Starting fallback agent loop")
    current_prompt = prompt
    for step in range(max_steps):
        logger.info("LLM -> step %d", step + 1)
        resp = ollama.generate(current_prompt)
        text = resp.get("text", "")
        logger.debug("LLM output: %s", text)

        tc = OllamaClient.extract_tool_call(text)
        if not tc:
            logger.info("No tool_call detected. Final LLM output:\n%s", text)
            return

        name = tc.get("name")
        args = tc.get("args", {})
        logger.info("Parsed tool_call: %s %s", name, args)

        # 查找工具
        tool = next((t for t in tools_meta if t["name"] == name), None)
        if not tool:
            logger.error("Unknown tool requested: %s", name)
            return

        # 执行工具
        try:
            raw_result = tool["func"](**args)
            raw_result = tool["func"](**args)
            logger.info("Tool %s result: %s", name, json.dumps(raw_result, ensure_ascii=False)[:1000])
            # 将结果反馈给 LLM 以进行下步计划
            current_prompt = f"Tool result for {name}: {json.dumps(raw_result, ensure_ascii=False)}\n\nNext:" + "\n"
        except PermissionError as e:
            logger.warning("Tool %s blocked by policy: %s", name, e)
            return
        except Exception as e:
            logger.exception("Tool execution failed: %s", e)
            return

    logger.info("Reached max steps (%d) without finalizing", max_steps)


def main():
    ollama = OllamaClient(base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
                          model=os.environ.get("OLLAMA_MODEL", "ollama"))
    tools = make_langchain_tools()
    prompt = os.environ.get("AGENT_PROMPT", "Perform analysis: ping and read memory at 0x401000")
    run_with_langchain(prompt, ollama, tools)


if __name__ == "__main__":
    main()