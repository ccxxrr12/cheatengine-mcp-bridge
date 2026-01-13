"""Agent runner for Prean C (agent as controller).

此模块启动 LangChain agent（若可用）并将 Cheat Engine 工具注册为工具库。
设计目标：生产就绪的最小控制器，包含审计日志、dry-run、破坏性审批检查与重试策略。
"""
from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.tools import Tool

# 尝试不同的导入方式以兼容不同版本的LangChain
try:
    # 最新版LangChain - create_agent
    from langchain.agents import create_agent
    from langchain.agents import AgentExecutor
    create_react_agent = create_agent
except ImportError:
    try:
        # 旧版LangChain - create_react_agent
        from langchain.agents import create_react_agent
        from langchain.agents import AgentExecutor
    except ImportError:
        try:
            # 从langgraph导入（兼容版）
            from langgraph.prebuilt import create_react_agent
            from langgraph.prebuilt import create_react_agent as AgentExecutor
        except ImportError:
            # 回退到内置执行循环
            create_react_agent = None
            AgentExecutor = None
from langchain_core.prompts import PromptTemplate
from langchain_ollama import ChatOllama

from ..config import settings
from .ollama_adapter import OllamaClient
from .ce_tools import make_langchain_tools, build_tool_metadata

# 配置日志
logging.basicConfig(level=settings.AGENT_LOG_LEVEL)
logger = logging.getLogger("mcp_agent")

# 创建日志目录和日志文件
log_dir = settings.LOG_DIR
os.makedirs(log_dir, exist_ok=True)
log_filename = os.path.join(log_dir, f"agent_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

def log_raw_response(response_data):
    """将原始响应写入日志文件"""
    with open(log_filename, 'a', encoding='utf-8') as log_file:
        log_file.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')}] Raw Response:\n")
        log_file.write(json.dumps(response_data, ensure_ascii=False, indent=2))
        log_file.write("\n" + "="*80 + "\n")

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
        # 检查create_react_agent是否可用
        if create_react_agent is None:
            logger.error("create_react_agent not available, falling back to direct loop")
            run_fallback_loop(prompt, ollama, tools, steps)
            return
            
        # 创建ChatOllama实例
        llm = ChatOllama(
            base_url=ollama.base_url,
            model=ollama.model,
            temperature=0.0
        )
        
        logger.info(f"Using Ollama model: {ollama.model} at {ollama.base_url}")

        # 创建代理提示
        agent_prompt = PromptTemplate(
            input_variables=["input", "agent_scratchpad"],
            template="""
            You are a Cheat Engine memory analysis assistant. Use the available tools to help analyze memory and answer user queries.

            Input: {input}

            Scratchpad:
            {agent_scratchpad}

            Instructions:
            1. Analyze the user's request
            2. Use the appropriate tools to gather information
            3. Analyze the results and provide a comprehensive answer
            4. If you need more information, ask the user for clarification
            """
        )

        # 处理不同版本的API
        try:
            # 尝试使用model参数（最新版）
            agent = create_react_agent(
                model=llm,
                tools=tools
            )
            
            logger.info("Starting agent (LangChain - model parameter) for prompt: %s", prompt)
            result = agent.invoke({"input": prompt})
        except TypeError:
            try:
                # 尝试使用llm参数（旧版）
                agent = create_react_agent(
                    llm=llm,
                    tools=tools,
                    prompt=agent_prompt
                )

                # 创建代理执行器
                agent_executor = AgentExecutor(
                    agent=agent,
                    tools=tools,
                    verbose=True,
                    handle_parsing_errors=True
                )

                logger.info("Starting agent (LangChain - llm parameter) for prompt: %s", prompt)
                result = agent_executor.invoke({"input": prompt})
            except Exception as e:
                logger.exception("Failed to create agent: %s", e)
                run_fallback_loop(prompt, ollama, tools, steps)
                return
        
        logger.info("Agent finished. Result:\n%s", result)
        print(f"\n✅ 分析完成，最终结果:")
        print(result.get("output", "No output available"))
    except Exception as e:
        logger.exception("LangChain integration failed, falling back to direct loop: %s", e)
        run_fallback_loop(prompt, ollama, tools, steps)


def run_fallback_loop(prompt: str, ollama: OllamaClient, tools_meta: List[Dict[str, Any]], max_steps: int = settings.MAX_AGENT_STEPS) -> None:
    """当没有 langchain 或集成失败时使用的回退调度器。

    协议约定：OLLAMA 输出应包含可解析的工具调用 JSON（见 ollama_adapter.extract_tool_call）。
    """
    print(f"\n🔍 开始分析请求: {prompt}")
    print("="*60)
    
    logger.info("Starting fallback agent loop")
    current_prompt = prompt
    
    for step in range(max_steps):
        logger.info("LLM -> step %d", step + 1)
        print(f"\n🔄 执行步骤 {step + 1}/{max_steps}")
        
        try:
            # 添加超时处理
            start_time = time.time()
            resp = ollama.generate(current_prompt)
            elapsed = time.time() - start_time
            
            text = resp.get("text", "")
            raw = resp.get("raw", {})
            
            # 记录原始响应到日志文件
            log_raw_response(resp)
            
            # 提取模型输出内容
            if isinstance(raw, dict):
                thinking = raw.get("thinking", "")
                response = raw.get("response", "")
                
                if thinking:
                    print(f"💡 模型思考: {thinking}")
                if response:
                    print(f"💬 模型回复: {response}")
            else:
                # 如果raw不是字典，尝试从text中提取内容
                if text.strip():
                    print(f"💬 模型回复: {text}")
            
            # 尝试从text中提取工具调用
            tc = OllamaClient.extract_tool_call(text)
            if not tc:
                # 尝试从raw响应中提取
                if isinstance(raw, str):
                    import re
                    matches = re.findall(r'"response":"([^"]*)"', raw)
                    if matches:
                        extracted_text = matches[-1]
                        tc = OllamaClient.extract_tool_call(extracted_text)
            
            if not tc:
                logger.info("No tool_call detected. Final LLM output:\n%s", text)
                print(f"\n✅ 分析完成，最终结果:")
                if isinstance(raw, dict) and "response" in raw:
                    print(f"{raw['response']}")
                else:
                    print(f"{text}")
                return

            name = tc.get("name")
            args = tc.get("args", {})
            logger.info("Parsed tool_call: %s %s", name, args)
            print(f"🔧 工具调用: {name}({args})")

            # 查找工具
            tool = next((t for t in tools_meta if t["name"] == name), None)
            if not tool:
                logger.error("Unknown tool requested: %s", name)
                print(f"❌ 错误: 未知工具 {name}")
                return

            # 执行工具
            try:
                raw_result = tool["func"](**args)
                logger.info("Tool %s result: %s", name, json.dumps(raw_result, ensure_ascii=False)[:1000])
                print(f"✅ 工具 {name} 执行成功")
                print(f"📊 结果摘要: {json.dumps(raw_result, ensure_ascii=False)[:500]}...")
                
                # 将结果反馈给 LLM 以进行下步计划
                current_prompt = f"Tool result for {name}: {json.dumps(raw_result, ensure_ascii=False)}\n\nNext:" + "\n"
            except PermissionError as e:
                logger.warning("Tool %s blocked by policy: %s", name, e)
                print(f"🚫 工具 {name} 被策略阻止: {e}")
                return
            except Exception as e:
                logger.exception("Tool execution failed: %s", e)
                print(f"💥 工具 {name} 执行失败: {e}")
                return
                
        except Exception as e:
            logger.exception("Error during step %d: %s", step + 1, e)
            print(f"💥 步骤 {step + 1} 执行出错: {e}")
            return

    logger.info("Reached max steps (%d) without finalizing", max_steps)
    print(f"\n⚠️  已达到最大步骤数 ({max_steps})，分析结束")


def run_interactive_mode(ollama: OllamaClient, tools: List[Any]):
    """交互式模式，允许用户输入多个请求"""
    print("🎮 欢迎使用Cheat Engine AI代理！")
    print("您可以提出内存分析相关的请求，例如：")
    print("- '找到游戏的金币地址并分析其修改函数'")
    print("- '分析玩家数据结构并提取所有相关字段'")
    print("- '找到数据包解密函数并生成解密脚本'")
    print("- 'ping并告诉我Cheat Engine的版本信息'")
    print("- '读取地址0x401000处的内存'")
    print("- 输入 'quit' 或 'exit' 退出程序\n")
    
    print(f"📋 日志文件位置: {log_filename}")
    
    while True:
        try:
            user_input = input("\n🎯 请输入您的请求（确保请求具体且明确）: ").strip()
            if user_input.lower() in ['quit', 'exit', 'q']:
                print("👋 再见！")
                break
            
            if not user_input:
                continue
                
            print(f"\n🚀 开始处理请求: {user_input}")
            run_with_langchain(user_input, ollama, tools)
            print("\n" + "="*60)
            
        except KeyboardInterrupt:
            print("\n\n🛑 程序被用户中断，再见！")
            break
        except Exception as e:
            logger.exception("处理用户请求时发生错误: %s", e)
            print(f"💥 发生错误: {e}")


def main():
    model_name = settings.OLLAMA_MODEL
    ollama = OllamaClient(base_url=settings.OLLAMA_URL,
                          model=model_name)
    tools = make_langchain_tools()
    prompt = settings.AGENT_PROMPT or "Perform analysis: ping and read memory at 0x401000"
    logger.info(f"Starting agent with model: {model_name}")
    
    # 检查是否设置了AGENT_PROMPT配置，如果没有，则进入交互模式
    if settings.AGENT_PROMPT:
        print(f"📋 日志文件位置: {log_filename}")
        print(f"🚀 执行配置请求: {prompt}")
        run_with_langchain(prompt, ollama, tools)
    else:
        print(f"📋 日志文件位置: {log_filename}")
        print("🎮 未设置AGENT_PROMPT配置，启动交互模式...")
        run_interactive_mode(ollama, tools)


if __name__ == "__main__":
    main()