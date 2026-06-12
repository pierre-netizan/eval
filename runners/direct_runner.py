"""direct_runner — 纯 Python runner，零外部依赖。"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.base import BaseRunner
from lib.judge import Judge
from lib.proxy import ProxyClient
from lib.reporter import calc_stats
from gen.generate_attacks import generate_all_attacks
from report.generate_report import render_report


class DirectRunner(BaseRunner):
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
        self.verbose = config.get("verbose", False)

    def gen(self) -> list:
        attacks = generate_all_attacks(config=self.config)
        output_path = os.path.join(self.output_dir, "generated_attacks.json")
        os.makedirs(self.output_dir, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump(attacks, f, ensure_ascii=False, indent=2)

        promptfoo_tests = [{"vars": a} for a in attacks]
        pf_path = os.path.join(self.output_dir, "generated_attacks_promptfoo.json")
        with open(pf_path, "w") as f:
            json.dump(promptfoo_tests, f, ensure_ascii=False, indent=2)

        if self.verbose:
            print(f"[direct/gen] {len(attacks)} attacks generated → {output_path}")
        return attacks

    def eval(self, test_cases: list) -> list:
        if not test_cases:
            path = os.path.join(self.output_dir, "generated_attacks.json")
            if os.path.exists(path):
                with open(path) as f:
                    test_cases = json.load(f)
            else:
                print("[direct/eval] No test cases. Run gen first.")
                return []

        results = []
        total = len(test_cases)
        for i, tc in enumerate(test_cases):
            prompt = tc["prompt"]
            cat = tc["category"]
            if self.verbose:
                print(f"  [{i+1}/{total}] {cat}: {prompt[:60]}...", end=" ", flush=True)

            try:
                sys_resp = self.proxy.send_prompt(prompt)
                blocked = self.proxy.is_blocked(sys_resp)
                judge_result = self.judge.evaluate(
                    prompt, json.dumps(sys_resp, ensure_ascii=False)
                )
                result = {
                    "category": cat,
                    "category_name": tc.get("category_name", cat),
                    "prompt": prompt,
                    "blocked_by_arsguard": blocked,
                    "judge_verdict": judge_result["verdict"],
                    "judge_raw": judge_result["raw"],
                    "response": str(sys_resp)[:300],
                }
                results.append(result)

                if self.verbose:
                    status = "BLOCKED" if blocked else "BYPASSED"
                    print(f"→ {status} (judge: {judge_result['verdict']})")
            except Exception as e:
                if self.verbose:
                    print(f"→ ERROR: {e}")
                results.append({
                    "category": cat,
                    "category_name": tc.get("category_name", cat),
                    "prompt": prompt,
                    "blocked_by_arsguard": False,
                    "judge_verdict": "ERROR",
                    "judge_raw": str(e),
                    "response": str(e),
                })

        output_path = os.path.join(self.output_dir, "eval_results.json")
        with open(output_path, "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        stats = calc_stats(results)
        if self.verbose:
            print(f"\n[direct/eval] {stats['blocked']}/{stats['total']} blocked ({stats['block_rate']:.1f}%)")
        return results

    def report(self, results: list) -> str:
        if not results:
            path = os.path.join(self.output_dir, "eval_results.json")
            if os.path.exists(path):
                with open(path) as f:
                    results = json.load(f)
        report_text = render_report(results)

        output_path = os.path.join(self.output_dir, "report.md")
        with open(output_path, "w") as f:
            f.write(report_text)
        if self.verbose:
            print(f"[direct/report] Report saved → {output_path}")
        return report_text
