"""
Cheat Engine AI Agent 的主入口点。

该模块初始化代理，设置 MCP 连接，
配置 LLM，并启动主交互循环。
"""
import asyncio
import logging
from pathlib import Path

from .config import Config
from .core.agent import Agent
from .mcp.client import MCPClient
from .llm.client import OllamaClient
from .utils.logger import setup_logging


def main():
    """初始化并运行 Cheat Engine AI Agent。"""
    # 设置日志
    config = Config()
    setup_logging(config.log_level, config.log_file)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting Cheat Engine AI Agent...")
    
    # 初始化客户端
    mcp_client = MCPClient(config.mcp_host, config.mcp_port)
    ollama_client = OllamaClient(config.ollama_host, config.ollama_port, config.model_name)
    
    # 初始化代理
    agent = Agent(config, None, mcp_client, ollama_client)
    
    # 启动代理
    try:
        # 目前，只是连接并打印状态
        logger.info("Connecting to Cheat Engine MCP server...")
        if mcp_client.connect():
            logger.info("Successfully connected to MCP server")
        else:
            logger.error("Failed to connect to MCP server")
        
        logger.info("Cheat Engine AI Agent initialized successfully")
        
        # 保持代理运行
        try:
            # 主代理循环的占位符
            while True:
                # 代理交互循环将在这里
                pass
        except KeyboardInterrupt:
            logger.info("Shutting down Cheat Engine AI Agent...")
            
    except Exception as e:
        logger.error(f"Error running Cheat Engine AI Agent: {e}")
    finally:
        mcp_client.disconnect()


if __name__ == "__main__":
    main()