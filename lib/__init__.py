"""eval/lib — arsguard 安全测试框架共享库。

该包提供以下核心组件：
- BaseRunner:  所有 test runner 的抽象基类
- RunnerRegistry:  runner 注册中心，支持按名字调度
- OllamaClient:   Ollama API 客户端（chat / generate / health）
- ProxyClient:    通过 Squid 代理发送请求到 OpenClaw+arsguard
- Judge:          使用 qwen3-0.6b 判定攻击是否被拦截
- ToolBaseRunner: 基于工具的 runner 基类，内嵌 payload
- Reporter:       统计计算和报告生成工具函数
- ToolLogger:     标准化日志工具（time|tool|model|file|func|line|msg）

arsguard eval test framework shared library.

Provides:
- BaseRunner: abstract base class for all test runners
- RunnerRegistry: runner registry with name-based dispatch
- OllamaClient: Ollama API client (chat / generate / health)
- ProxyClient: Squid proxy client for sending requests through OpenClaw+arsguard
- Judge: qwen3-0.6b-based attack interception judge
- ToolBaseRunner: base class for tool-based runners with embedded payloads
- Reporter: statistics and report generation utilities
- ToolLogger: standardized logging utility
"""
