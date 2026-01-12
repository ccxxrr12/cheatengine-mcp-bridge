# MCP LangChain Agent (预案 C) 使用说明

最小可运行骨架包含：

- `ollama_adapter.py`：与 Ollama HTTP API 的轻量适配器。
- `ce_tools.py`：将现有 Cheat Engine 桥接封装为可注册给 agent 的工具。
- `result_parsers.py`：pydantic 解析器，保证工具输出结构化。
- `error_policy.py`：生产级的重试与破坏性操作审批钩子。
- `agent_runner.py`：启动 agent 的入口，优先使用 LangChain；若不可用则回退到内置执行循环。

快速开始：

1. 安装依赖（建议使用虚拟环境）：

```bash
pip install -r requirements.txt
```

2. 配置环境变量（示例）:

```bash
export OLLAMA_URL=http://localhost:11434
export OLLAMA_MODEL=ollama
# 允许破坏性操作（测试时短期开启）
export AGENT_ALLOW_DESTRUCTIVE=0
```

3. 运行 agent（LangChain 可用时走 LangChain）:

```bash
python agent_runner.py
```

注意与安全：

- 生产环境必须替换 `require_destructive_approval` 中的审批逻辑为人工确认或集中策略引擎。
- agent 的行为、所有工具调用与 LLM prompts 应写入审计日志（可扩展日志处理）。
