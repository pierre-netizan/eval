"""Shared Ollama API client."""

import json
import urllib.request
import urllib.error


class OllamaClient:
    """Ollama API 客户端，支持 chat 和 generate。"""

    def __init__(self, host: str = "http://localhost:11434", timeout: int = 120):
        self.host = host.rstrip("/")
        self.timeout = timeout

    def chat(self, model: str, messages: list, **options) -> str:
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
                return data.get("message", {}).get("content", "")
        except urllib.error.HTTPError as e:
            body = e.read().decode()
            raise RuntimeError(f"Ollama API error {e.code}: {body}")
        except Exception as e:
            raise RuntimeError(f"Ollama request failed: {e}")

    def health(self) -> bool:
        try:
            req = urllib.request.Request(f"{self.host}/api/tags")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except Exception:
            return False
