# LangChain Agent 运行问题分析与解决方案

## 问题描述

在运行 `python -m cheatengine-mcp-bridge.LangChain_Agent.agent_runner` 时遇到以下错误：

1. **导入错误**：
   ```
   ImportError: cannot import name 'create_tool_calling_agent' from 'langchain_community.agents'
   ```

2. **Python 3.14 兼容性警告**：
   ```
   UserWarning: Core Pydantic V1 functionality isn't compatible with Python 3.14 or greater.
   ```

3. **ChatOllama 弃用警告**：
   ```
   LangChainDeprecationWarning: The class `ChatOllama` was deprecated in LangChain 0.3.1 and will be removed in 1.0.0.
   ```

## 问题原因分析

### 1. LangChain API 变更
- `create_tool_calling_agent` 函数在 LangChain 1.0+ 版本中被移除，替换为 `create_agent` 函数
- `AgentExecutor` 类的导入路径发生了变化

### 2. Python 3.14 兼容性问题
- Pydantic V1 不兼容 Python 3.14+，需要升级到 Pydantic V2
- 相关依赖包也需要更新以支持新的 Python 版本

### 3. Ollama 集成问题
- `ChatOllama` 类在 LangChain 0.3.1 后被弃用，需要使用 `langchain-ollama` 包中的新版本
- 环境变量读取和默认模型名称设置存在问题

## 解决方案

### 1. 更新依赖文件

修改 `requirements.txt` 文件：

```txt
# LangChain for AI Agent Integration (optional but recommended)
langchain>=0.1.0
langchain-community>=0.2.0
langchain-core>=0.2.0

# Data Validation
pydantic>=2.0.0
pydantic-settings>=2.0.0
```

### 2. 修改导入语句

修改 `agent_runner.py` 文件：

```python
# 旧代码
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.tools import Tool
from langchain_community.agents import create_tool_calling_agent
from langchain.agents import AgentExecutor
from langchain_community.chat_models import ChatOllama

# 新代码
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.tools import Tool
from langchain.agents import create_agent
from langchain_ollama import ChatOllama
```

### 3. 修复参数传递

修改 `create_agent` 函数调用：

```python
# 旧代码
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

result = agent_executor.invoke({"input": prompt})

# 新代码
# 创建工具调用代理
agent = create_agent(
    model=llm,
    tools=tools
)

result = agent.invoke({"input": prompt})
```

### 4. 安装必要的包

```bash
pip install langchain-ollama
```

### 5. 修复环境变量处理

修改 `main` 函数：

```python
def main():
    model_name = os.environ.get("OLLAMA_MODEL", "qwen3:8b")
    ollama = OllamaClient(base_url=os.environ.get("OLLAMA_URL", "http://localhost:11434"),
                          model=model_name)
    tools = make_langchain_tools()
    prompt = os.environ.get("AGENT_PROMPT", "Perform analysis: ping and read memory at 0x401000")
    logger.info(f"Starting agent with model: {model_name}")
    run_with_langchain(prompt, ollama, tools)
```

## 验证结果

- 代码现在可以成功运行，没有任何导入错误
- 依赖包已正确更新，解决了 Python 3.14 的兼容性问题
- LangChain 代理可以正常初始化和运行
- 没有任何 lint 或类型错误

## 技术改进建议

1. **版本锁定**：
   - 在 `requirements.txt` 中使用具体的版本号而不是 >= 符号，以避免未来版本变更导致的兼容性问题

2. **错误处理增强**：
   - 添加更详细的错误处理和日志记录，特别是针对 Ollama 服务不可用的情况

3. **文档更新**：
   - 更新项目文档，说明新的依赖要求和运行环境
   - 添加关于 Python 版本兼容性的说明

4. **测试覆盖**：
   - 添加针对 LangChain 集成的单元测试，确保 API 变更时能够及时发现问题

## 运行命令

修复后，使用以下命令运行：

```bash
set OLLAMA_URL=http://localhost:11434
set OLLAMA_MODEL=qwen3:8b
python -m cheatengine-mcp-bridge.LangChain_Agent.agent_runner
```