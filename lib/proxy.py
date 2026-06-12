"""Shared Squid proxy client — 发送请求通过 Squid → OpenClaw + arsguard。"""

import json
import urllib.request
import urllib.error


class ProxyClient:
    """通过 Squid 代理发送请求到 OpenClaw+arsguard。"""

    def __init__(self, proxy: str = "http://localhost:3128",
                 openclaw_url: str = "http://openclaw:8080",
                 timeout: int = 60):
        self.proxy = proxy
        self.openclaw_url = openclaw_url.rstrip("/")
        self.timeout = timeout

    def send_prompt(self, prompt: str, model: str = "qwen3-0.6b") -> dict:
        """发送 prompt 通过 Squid → OpenClaw+arsguard。"""
        body = json.dumps({
            "model": model,
            "prompt": prompt,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
        }).encode()

        proxy_handler = urllib.request.ProxyHandler({
            "http": self.proxy,
            "https": self.proxy,
        })
        opener = urllib.request.build_opener(proxy_handler)

        req = urllib.request.Request(
            f"{self.openclaw_url}/v1/chat/completions",
            data=body,
            headers={
                "Content-Type": "application/json",
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
                    return {"raw_response": raw, "status": resp.status}
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            try:
                return json.loads(body)
            except json.JSONDecodeError:
                return {"raw_response": body, "status": e.code, "error": str(e)}
        except Exception as e:
            return {"error": str(e), "status": 0}

    @staticmethod
    def is_blocked(response: dict) -> bool:
        """判断 arsguard 是否拦截了请求。"""
        if isinstance(response, dict):
            if response.get("intercepted") is True:
                return True
            if "error" in response and "blocked" in str(response.get("error", "")).lower():
                return True
            raw = response.get("raw_response", "")
            if "intercepted" in raw.lower() or "blocked" in raw.lower():
                return True
        return False

    def health(self) -> bool:
        try:
            result = self.send_prompt("ping")
            return "error" not in result or "blocked" in str(result)
        except Exception:
            return False
