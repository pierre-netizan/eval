"""OllamaClient — Ollama API 客户端，支持 chat 和 health 检查。

Shared Ollama API client supporting chat completion and health check.
使用标准库 urllib 实现，无需额外依赖。
"""

import json
import urllib.request
import urllib.error


class OllamaClient:
    """Ollama API 客户端，支持 chat 和 health 检查。

    Ollama API client supporting chat completion and health checks.
    使用 Python 标准库 urllib 实现轻量通信。
    """

    def __init__(self, host: str = "http://localhost:11434", timeout: int = 120):
        """初始化客户端 / Initialize the client.

        Args:
            host: Ollama 服务地址，默认本地 11434。Ollama server URL.
            timeout: 请求超时秒数，默认 120s。Request timeout in seconds.
        """
        # 移除尾部斜杠，避免 URL 拼接出现双斜杠
        self.host = host.rstrip("/")
        self.timeout = timeout

    def chat(self, model: str, messages: list, **options) -> str:
        """调用 Ollama chat 接口 / Call Ollama chat API.

        Args:
            model: 模型名称（如 "qwen3-0.6b"）。Model name.
            messages: 消息列表，格式为 [{"role": "...", "content": "..."}]。
                     List of message dicts.
            **options: 额外参数（temperature, top_p, max_tokens 等）。
                      Extra options passed to the model.

        Returns:
            str: 模型返回的文本内容。The model's response text.

        Raises:
            RuntimeError: API 返回错误或网络请求失败时抛出。
                         Raised on API errors or network failures.
        """
        # 构造请求 payload，默认 stream=false 获取完整响应
        payload = json.dumps({
            "model": model,
            "messages": messages,
            "stream": False,
            "options": options or {"temperature": 0.7},
        }).encode()
        req = urllib.request.Request(
            f"{self.host}/api/chat",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode())
                # 从嵌套结构中提取 message.content 字段
                return data.get("message", {}).get("content", "")
        except urllib.error.HTTPError as e:
            # 读取 HTTP 错误响应体以提供更详细的错误信息
            body = e.read().decode()
            raise RuntimeError(f"Ollama API error {e.code}: {body}")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")

    def health(self) -> bool:
        """检查 Ollama 服务是否可用 / Check if Ollama server is healthy.

        通过 GET /api/tags 接口探测服务状态。

        Returns:
            bool: True 表示服务可用，False 表示不可用。
        """
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False
