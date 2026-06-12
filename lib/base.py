from abc import ABC, abstractmethod


class BaseRunner(ABC):
    """所有 test runner 的抽象基类。
    
    子类需实现 gen/eval/report 三个阶段。
    """

    def __init__(self, config: dict):
        self.config = config
        self.ollama_cfg = config.get("ollama", {})
        self.squid_cfg = config.get("squid", {})
        self.output_dir = config.get("output_dir", "data")

    @abstractmethod
    def gen(self) -> list:
        """生成测试用例。
        
        Returns:
            list[dict]: 测试用例列表，每项含 category/prompt 等字段。
        """
        ...

    @abstractmethod
    def eval(self, test_cases: list) -> list:
        """执行测试。
        
        Args:
            test_cases: gen() 返回的测试用例。
        
        Returns:
            list[dict]: 测试结果列表，每项含 category/blocked/judge_verdict 等字段。
        """
        ...

    @abstractmethod
    def report(self, results: list) -> str:
        """生成测试报告。
        
        Args:
            results: eval() 返回的测试结果。
        
        Returns:
            str: 报告内容（Markdown 格式）。
        """
        ...

    def run_all(self) -> dict:
        """运行全流程：gen → eval → report。"""
        test_cases = self.gen()
        results = self.eval(test_cases)
        report = self.report(results)
        return {"test_cases": test_cases, "results": results, "report": report}
