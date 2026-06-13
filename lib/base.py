"""BaseRunner — 所有 test runner 的抽象基类 / Abstract base class for all test runners.

三阶段流水线：gen（生成测试用例）→ eval（执行测试）→ report（生成报告）。
Three-phase pipeline: gen → eval → report.
"""

from abc import ABC, abstractmethod


class BaseRunner(ABC):
    """所有 test runner 的抽象基类，定义三阶段流水线接口。

    Abstract base class for all test runners, defining the three-phase pipeline interface.

    子类必须实现 gen()、eval()、report() 三个方法。
    Subclasses must implement gen(), eval(), report().
    """

    def __init__(self, config: dict):
        """初始化 runner。

        Args:
            config: 包含 ollama/squid/output_dir 等配置项的字典。Dict with ollama/squid/output_dir keys.
        """
        self.config = config
        # 从配置中提取 Ollama 相关设置（host, model 等）
        self.ollama_cfg = config.get("ollama", {})
        # 从配置中提取 Squid 代理相关设置（proxy, openclaw_url 等）
        self.squid_cfg = config.get("squid", {})
        # 输出目录，默认为 "data"
        self.output_dir = config.get("output_dir", "data")

    @abstractmethod
    def gen(self) -> list:
        """生成测试用例 / Generate test cases.

        Returns:
            list[dict]: 测试用例列表，每项含 category/prompt/tool 等字段。
                        List of test cases, each containing category/prompt/tool etc.
        """
        ...

    @abstractmethod
    def eval(self, test_cases: list) -> list:
        """执行测试 / Execute test cases against arsguard.

        Args:
            test_cases: gen() 返回的测试用例列表。Test cases from gen().

        Returns:
            list[dict]: 测试结果列表，每项含 category/blocked_by_arsguard/judge_verdict 等字段。
                        List of results, each containing category/blocked_by_arsguard/judge_verdict etc.
        """
        ...

    @abstractmethod
    def report(self, results: list) -> str:
        """生成测试报告 / Generate a test report.

        Args:
            results: eval() 返回的测试结果列表。Results from eval().

        Returns:
            str: 报告内容（Markdown 格式）。Report content in Markdown format.
        """
        ...

    def run_all(self) -> dict:
        """运行全流程：gen → eval → report / Run the full pipeline.

        Returns:
            dict: {"test_cases": ..., "results": ..., "report": ...}
        """
        test_cases = self.gen()
        results = self.eval(test_cases)
        report = self.report(results)
        return {"test_cases": test_cases, "results": results, "report": report}
