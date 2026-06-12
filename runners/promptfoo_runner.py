"""promptfoo_runner — 用 promptfoo CLI 执行 gen/eval。"""

import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.base import BaseRunner
from lib.judge import Judge
from lib.proxy import ProxyClient
from lib.reporter import calc_stats
from report.generate_report import render_report


class PromptfooRunner(BaseRunner):
    """通过 promptfoo CLI 运行测试。需要 promptfoo 已安装 (npx promptfoo)。"""

    def __init__(self, config: dict):
        super().__init__(config)
        self.judge = Judge(
            model=self.ollama_cfg.get("target_model", "qwen3-0.6b"),
            host=self.ollama_cfg.get("host", "http://localhost:11434"),
        )
        self.proxy = ProxyClient(
            proxy=self.squid_cfg.get("proxy", "http://localhost:3128"),
            openclaw_url=self.squid_cfg.get("openclaw_url", "http://openclaw:8080"),
        )
        self.promptfoo_dir = os.path.join(os.path.dirname(__file__), "..", "config", "promptfoo")

    def gen(self) -> list:
        config_path = os.path.join(self.promptfoo_dir, "gen_config.yaml")
        output_path = os.path.join(self.output_dir, "promptfoo_gen_output.json")

        cmd = [
            "npx", "promptfoo", "eval",
            "--config", config_path,
            "--output", output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"[promptfoo/gen] ERROR: {result.stderr}", file=sys.stderr)
            return []

        # Convert promptfoo output to standard format
        if os.path.exists(output_path):
            with open(output_path) as f:
                raw = json.load(f)
            attacks = self._parse_output(raw)
            std_path = os.path.join(self.output_dir, "generated_attacks.json")
            with open(std_path, "w") as f:
                json.dump(attacks, f, ensure_ascii=False, indent=2)
            print(f"[promptfoo/gen] {len(attacks)} attacks generated")
            return attacks
        return []

    def eval(self, test_cases: list) -> list:
        config_path = os.path.join(self.promptfoo_dir, "promptfooconfig.yaml")
        output_path = os.path.join(self.output_dir, "promptfoo_eval_output.json")

        cmd = [
            "npx", "promptfoo", "eval",
            "--config", config_path,
            "--output", output_path,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"[promptfoo/eval] ERROR: {result.stderr}", file=sys.stderr)
            return []

        if os.path.exists(output_path):
            with open(output_path) as f:
                raw = json.load(f)
            results = self._parse_eval_output(raw)

            # Run judge on results
            for r in results:
                if r.get("judge_verdict") != "ERROR":
                    jr = self.judge.evaluate(r["prompt"], r.get("response", ""))
                    r["judge_verdict"] = jr["verdict"]
                    r["judge_raw"] = jr["raw"]

            std_path = os.path.join(self.output_dir, "eval_results.json")
            with open(std_path, "w") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            return results
        return []

    def report(self, results: list) -> str:
        return render_report(results)

    def _parse_output(self, raw: list) -> list:
        attacks = []
        for item in raw:
            if isinstance(item, dict):
                vars_ = item.get("vars", item)
                attacks.append({
                    "category": vars_.get("category", "unknown"),
                    "prompt": vars_.get("prompt", ""),
                })
        return attacks

    def _parse_eval_output(self, raw: list) -> list:
        results = []
        for item in raw:
            if isinstance(item, dict):
                vars_ = item.get("vars", item)
                prompt = vars_.get("prompt", "")
                outputs = item.get("outputs", [])
                response = outputs[0] if outputs else ""
                results.append({
                    "category": vars_.get("category", "unknown"),
                    "category_name": vars_.get("category_name", vars_.get("category", "")),
                    "prompt": prompt,
                    "blocked_by_arsguard": "BLOCKED" in str(response),
                    "judge_verdict": "PENDING",
                    "response": str(response)[:300],
                })
        return results
