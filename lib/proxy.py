"""ProxyClient — 通过 Squid 代理发送请求到 OpenClaw + arsguard。

Sends requests through Squid proxy to OpenClaw + arsguard for security testing.
所有请求都经过 Squid:3128 代理，确保测试环境与实际部署一致。
"""

import json
import urllib.request
import urllib.error


class ProxyClient:
    """通过 Squid 代理发送请求到 OpenClaw+arsguard 的客户端。

    Client for sending prompts through Squid proxy to OpenClaw+arsguard.
    请求路径：Client → Squid:3128 → OpenClaw:8080 → arsguard 钩子链 → 目标模型。
    """

    def __init__(self, proxy: str = "http://localhost:3128",
                 openclaw_url: str = "http://openclaw:8080",
                 timeout: int = 60):
        """初始化代理客户端 / Initialize the proxy client.

        Args:
            proxy: Squid 代理地址。Squid proxy URL.
            openclaw_url: OpenClaw 服务地址（内部网络）。OpenClaw server URL (internal network).
            timeout: 请求超时秒数，默认 60s。Request timeout in seconds.
        """
        self.proxy = proxy
        # 移除尾部斜杠，避免 URL 拼接问题
        self.openclaw_url = openclaw_url.rstrip("/")
        self.timeout = timeout

    def send_prompt(self, prompt: str, model: str = "qwen3-0.6b") -> dict:
        """发送 prompt 通过 Squid → OpenClaw+arsguard。

        Sends a prompt through Squid proxy to OpenClaw+arsguard.

        请求经过 Squid 代理转发到 OpenClaw 的 /v1/chat/completions 端点，
        arsguard 插件会在此过程中对请求进行安全检查。

        Args:
            prompt: 用户输入的提示词。The user prompt to send.
            model: 目标模型名称。Target model name.

        Returns:
            dict: 如果响应是 JSON 则返回解析后的字典；否则返回包含 raw_response 和 status 的字典。
                  Parsed JSON dict if response is JSON, or dict with raw_response/status.
        """
        # 构造与 OpenAI API 兼容的请求体
        body = json.dumps({
            "model": model,
            "prompt": prompt,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }).encode()

        # 配置 HTTP/HTTPS 代理处理器
        proxy_handler = urllib.request.ProxyHandler({
            "http": self.proxy,
            "https": self.proxy,
        })
        opener = urllib.request.build_opener(proxy_handler)

        # 构造请求，添加 X-Forwarded-For 模拟外部来源以触发安全检测
        req = urllib.request.Request(
            f"{self.openclaw_url}/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
                # 模拟外部 IP 以触发 arsguard 的安全检测
                "X-Forwarded-For": "10.0.0.1",
            },
            method="POST",
        )

        try:
            with opener.open(req, timeout=self.timeout) as resp:
                raw = resp.read().decode()
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    # 非 JSON 响应（如被 Squid 拦截的 HTML 页面）也记录下来
                    return {"raw_response": raw, "status": resp.status}
        except urllib.error.HTTPError as e:
            # HTTP 错误（4xx/5xx）可能包含 JSON 错误体或纯文本
            body = e.read().decode()
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {"raw_response": body, "status": e.code, "error": str(e)}
        except Exception as e:
            # 网络错误、超时等其他异常
            return {"error": str(e), "status": 0}

    @staticmethod
    def is_blocked(response: dict) -> bool:
        """判断 arsguard 是否拦截了请求 / Check if arsguard blocked the request.

        通过检查响应中的以下标志判断拦截：
        - intercepted: true 字段（arsguard 标准拦截标志）
        - error 字段包含 "blocked" 关键字
        - raw_response 文本包含 "intercepted" 或 "blocked"

        Args:
            response: send_prompt() 返回的响应字典。Response dict from send_prompt().

        Returns:
            bool: True 表示请求被拦截，False 表示请求通过。
        """
        if isinstance(response, dict):
            # 标准拦截标志：arsguard 返回 {"intercepted": true}
            if response.get("intercepted") is True:
                return True
            # 错误信息中包含 "blocked" 关键字
            if "error" in response and "blocked" in str(response.get("error", "")).lower():
                return True
            # 原始响应文本中包含拦截关键词（如 Squid 返回的 HTML 错误页）
            raw = response.get("raw_response", "")
            if "intercepted" in raw.lower() or "blocked" in raw.lower():
                return True
        return False

    def health(self) -> bool:
        """检查 Squid + OpenClaw 代理链路是否可用 / Check if the proxy chain is healthy.

        发送一个简单的 "ping" prompt，验证整个链路是否通畅。

        Returns:
            bool: True 表示代理链路可达，False 表示不可用。
        """
        try:
            result = self.send_prompt("ping")
            # 即使返回 "blocked" 也说明链路是通的
            return "error" not in result or "blocked" in str(result)
        except Exception:
            return False
