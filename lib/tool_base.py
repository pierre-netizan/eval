"""ToolBaseRunner — 基于工具的 runner 基类，内嵌 payload 文件直接定义攻击用例。

Base class for tool-based runners with embedded payloads.
子类只需定义三个类属性：
    tool_name: str  — 工具名称 (e.g. "hackmyagent")
    payloads: dict  — 攻击用例字典 (category_id -> list[str] 或 list[dict])
    names: dict     — 类别显示名称 (category_id -> display name)
"""

import json
import os
import sys

# 将项目根目录加入路径，确保可以 import lib.* 模块
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.base import BaseRunner
from lib.judge import Judge
from lib.proxy import ProxyClient
from lib.reporter import calc_stats, gen_metadata, eval_metadata, save_json


class ToolBaseRunner(BaseRunner):
    """基于工具的 runner 基类，内嵌 payload 直接定义攻击用例。

    Base class for tool-based runners with embedded payloads.
    子类覆盖 tool_name/payloads/names 三个类属性即可完成自定义。
    """

    # 子类必须覆盖以下类属性
    tool_name = "tool"          # 工具名称，用于标识和文件命名
    payloads = {}               # 攻击用例：{category_id: [prompt_str 或 dict]}
    names = {}                  # 类别显示名称：{category_id: display_name}

    def __init__(self, config: dict):
        """初始化 runner，创建 Judge 和 ProxyClient 实例。

        Args:
            config: 配置字典（包含 ollama/squid/verbose 等）。Configuration dict.
        """
        super().__init__(config)
        # 初始化法官，用于后续判定拦截效果
        self.judge = Judge(
            model=self.ollama_cfg.get("target_model", "qwen3-0.6b"),
            host=self.ollama_cfg.get("host", "http://localhost:11434"),
        )
        # 初始化代理客户端，用于发送测试请求
        self.proxy = ProxyClient(
            proxy=self.squid_cfg.get("proxy", "http://localhost:3128"),
            openclaw_url=self.squid_cfg.get("openclaw_url", "http://openclaw:8080"),
        )
        # 是否输出详细日志
        self.verbose = config.get("verbose", False)

    def gen(self) -> list:
        """生成测试用例 / Generate test cases from embedded payloads.

        遍历 self.payloads 字典，支持两种格式：
        - str: 直接作为 prompt
        - dict: 包含 "prompt" 键以及可选的 "subcategory"/"subcategory_name"

        同时生成两种输出：
        - generated_attacks.json:          标准格式测试用例
        - generated_attacks_promptfoo.json: promptfoo 兼容格式

        Returns:
            list[dict]: 测试用例列表，每项含 category/category_name/prompt/tool/tool_id 等字段。
        """
        attacks = []
        # 遍历每个类别的所有 prompts
        for cat_id, prompts in self.payloads.items():
            for i, p in enumerate(prompts, 1):
                # 支持 dict 格式（带 subcategory 信息）和 str 格式
                if isinstance(p, dict):
                    prompt_text = p["prompt"]
                    subcat = p.get("subcategory", "")
                    subcat_name = p.get("subcategory_name", "")
                else:
                    prompt_text = p
                    subcat = ""
                    subcat_name = ""
                attacks.append({
                    "category": cat_id,
                    "category_name": self.names.get(cat_id, cat_id),
                    "prompt": prompt_text,
                    "tool": self.tool_name,
                    "tool_id": f"{cat_id}-{self.tool_name}-{i:03d}",
                    "tool_subcategory": subcat,
                    "tool_subcategory_name": subcat_name,
                })
        os.makedirs(self.output_dir, exist_ok=True)

        # 输出标准格式（供 direct_runner 使用）
        path = os.path.join(self.output_dir, "generated_attacks.json")
        with open(path, "w") as f:
            json.dump(attacks, f, ensure_ascii=False, indent=2)

        # 输出 promptfoo 兼容格式（vars 包裹）
        pf_path = os.path.join(self.output_dir, "generated_attacks_promptfoo.json")
        pf_tests = [{"vars": a} for a in attacks]
        with open(pf_path, "w") as f:
            json.dump(pf_tests, f, ensure_ascii=False, indent=2)

        # 生成阶段元数据
        meta = gen_metadata(attacks, {**self.config, "runner": self.tool_name})
        save_json(meta, os.path.join(self.output_dir, "gen_report.json"))

        if self.verbose:
            print(f"[{self.tool_name}/gen] {len(attacks)} attacks")
        return attacks

    def eval(self, test_cases: list) -> list:
        """执行测试 / Execute test cases against arsguard.

        对每个测试用例：
        1. 通过 ProxyClient 发送 prompt → Squid → OpenClaw+arsguard
        2. 通过 ProxyClient.is_blocked() 判断 arsguard 是否拦截
        3. 通过 Judge.evaluate() 使用 qwen3-0.6b 进行独立判定

        如果 test_cases 为空，尝试从 generated_attacks.json 加载。

        Args:
            test_cases: gen() 返回或从文件加载的测试用例列表。
                       If empty, attempts to load from generated_attacks.json.

        Returns:
            list[dict]: 测试结果列表，每项含 category/prompt/blocked_by_arsguard/judge_verdict 等字段。
        """
        # 如果没有传入测试用例，从文件加载
        if not test_cases:
            path = os.path.join(self.output_dir, "generated_attacks.json")
            if os.path.exists(path):
                with open(path) as f:
                    test_cases = json.load(f)
            else:
                print(f"[{self.tool_name}/eval] No test cases. Run gen first.")
                return []

        results = []
        total = len(test_cases)
        # 逐个执行测试用例
        for i, tc in enumerate(test_cases):
            prompt = tc["prompt"]
            cat = tc["category"]
            if self.verbose:
                print(f"  [{i+1}/{total}] {cat}: {prompt[:60]}...", end=" ", flush=True)

            try:
                # 发送请求并获取结果
                sys_resp = self.proxy.send_prompt(prompt)
                blocked = self.proxy.is_blocked(sys_resp)
                # 使用法官模型进行独立判定
                judge_result = self.judge.evaluate(prompt, json.dumps(sys_resp, ensure_ascii=False))
                result = {
                    "category": cat,
                    "category_name": tc.get("category_name", cat),
                    "prompt": prompt,
                    "blocked_by_arsguard": blocked,
                    "judge_verdict": judge_result["verdict"],
                    "judge_raw": judge_result["raw"],
                    "response": str(sys_resp)[:300],
                    "tool": tc.get("tool", self.tool_name),
                    "tool_id": tc.get("tool_id", ""),
                }
                results.append(result)
                if self.verbose:
                    print(f"\u2192 {'BLOCKED' if blocked else 'BYPASSED'} (judge: {judge_result['verdict']})")
            except Exception as e:
                # 异常处理：记录为 ERROR，避免单个失败中断整个 batch
                if self.verbose:
                    print(f"\u2192 ERROR: {e}")
                results.append({
                    "category": cat,
                    "category_name": tc.get("category_name", cat),
                    "prompt": prompt,
                    "blocked_by_arsguard": False,
                    "judge_verdict": "ERROR",
                    "judge_raw": str(e),
                    "response": str(e),
                    "tool": tc.get("tool", self.tool_name),
                    "tool_id": tc.get("tool_id", ""),
                })

        # 保存结果和元数据
        os.makedirs(self.output_dir, exist_ok=True)
        with open(os.path.join(self.output_dir, "eval_results.json"), "w") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        meta = eval_metadata(results, {**self.config, "runner": self.tool_name})
        save_json(meta, os.path.join(self.output_dir, "eval_report.json"))

        # 输出摘要
        stats = calc_stats(results)
        if self.verbose:
            print(f"\n[{self.tool_name}/eval] {stats['blocked']}/{stats['total']} blocked ({stats['block_rate']:.1f}%)")
        return results

    def report(self, results: list) -> str:
        """生成测试报告 / Generate a test report.

        调用 report.generate_report 模块渲染 Markdown 报告并保存多种格式。
        如果 results 为空，尝试从 eval_results.json 加载。

        Args:
            results: eval() 返回的测试结果列表。Results from eval(). Loads from file if empty.

        Returns:
            str: Markdown 格式的报告内容。Report content in Markdown format.
        """
        # 如果没传入结果，尝试从文件加载
        if not results:
            path = os.path.join(self.output_dir, "eval_results.json")
            if os.path.exists(path):
                with open(path) as f:
                    results = json.load(f)
        # 延迟导入，避免循环依赖
        from report.generate_report import render_markdown, save_reports
        # 保存多种格式报告（HTML, PDF 等）
        paths = save_reports(results, output_dir=self.output_dir, compile_pdf=True,
                             filename_prefix=f"report_{self.tool_name}",
                             tool_label=self.tool_name)
        if self.verbose:
            for fmt, p in paths.items():
                print(f"[{self.tool_name}/report] {fmt} \u2192 {p}")
        return render_markdown(results, tool_label=self.tool_name)
