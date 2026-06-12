"""promptfoo custom provider — sends prompts through Squid → OpenClaw + arsguard."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.proxy import ProxyClient
from lib.judge import Judge


def call_api(prompt: str, options: dict = None, context: dict = None) -> dict:
    """promptfoo custom provider entry point."""
    proxy = ProxyClient(
        proxy=os.environ.get("SQUID_PROXY", options.get("squid_proxy", "http://localhost:3128")) if options else os.environ.get("SQUID_PROXY", "http://localhost:3128"),
        openclaw_url=os.environ.get("OPENCLAW_URL", options.get("openclaw_url", "http://openclaw:8080")) if options else os.environ.get("OPENCLAW_URL", "http://openclaw:8080"),
    )
    judge = Judge(
        model=os.environ.get("TARGET_MODEL", "qwen3-0.6b"),
        host=os.environ.get("OLLAMA_HOST", "http://localhost:11434"),
    )

    sys_resp = proxy.send_prompt(prompt)
    blocked = proxy.is_blocked(sys_resp)
    judge_result = judge.evaluate(prompt, json.dumps(sys_resp, ensure_ascii=False))

    output = json.dumps({
        "prompt": prompt[:200],
        "system_response": str(sys_resp)[:500],
        "blocked": blocked,
        "judge_verdict": judge_result["verdict"],
        "judge_raw": judge_result["raw"],
    }, ensure_ascii=False)

    return {
        "output": output,
        "tokenUsage": {"total": 0, "prompt": 0, "completion": 0},
    }
