"""RunnerRegistry — Runner 注册中心，支持按名字注册和调度。

Registry for test runners. Supports name-based registration and dispatch.
通过 register() 注册 runner 类，通过 run() 按名字自动调度执行。
"""


class RunnerRegistry:
    """Runner 注册中心。通过 register() 注册，run() 自动调度。

    Runner registry. Register runner classes with register(), dispatch with run().
    支持选择性执行某个或某些阶段（gen/eval/report）。
    """

    # 类级别字典，存储所有注册的 runner 类
    _runners = {}

    @classmethod
    def register(cls, name: str, runner_cls):
        """注册一个 runner / Register a runner class.

        Args:
            name: runner 名字（如 "direct", "promptfoo"）。Runner name.
            runner_cls: 继承 BaseRunner 的类。Class inheriting from BaseRunner.
        """
        cls._runners[name] = runner_cls

    @classmethod
    def get(cls, name: str):
        """获取已注册的 runner 类 / Get a registered runner class.

        Args:
            name: runner 名字。Runner name.

        Returns:
            type: 继承 BaseRunner 的类。The runner class.

        Raises:
            KeyError: 如果名字未注册。If name is not registered.
        """
        if name not in cls._runners:
            available = ", ".join(cls._runners.keys())
            raise KeyError(f"Unknown runner: {name}. Available: {available}")
        return cls._runners[name]

    @classmethod
    def list(cls) -> list:
        """列出所有已注册的 runner 名字 / List all registered runner names.

        Returns:
            list[str]: runner 名字列表。List of runner names.
        """
        return list(cls._runners.keys())

    @classmethod
    def run(cls, name: str, config: dict, phases: list = None) -> dict:
        """便捷方法：按名字运行 runner / Convenience method: run a runner by name.

        如果 phases 为 None 则运行全流程（gen → eval → report）；
        否则只运行指定的阶段，阶段间自动传递数据。

        Args:
            name: runner 名字。Runner name.
            config: 配置字典。Configuration dict.
            phases: 要运行的阶段列表，可选 "gen"/"eval"/"report" 的组合。
                   List of phases to run. If None, runs all phases.

        Returns:
            dict: 包含 test_cases / results / report 等字段的结果字典。
                  Result dict with test_cases/results/report keys.
        """
        runner_cls = cls.get(name)
        runner = runner_cls(config)
        # 未指定 phases 则运行全流程
        if phases is None:
            return runner.run_all()
        # 按指定阶段选择性执行，后一阶段可复用前一阶段的输出
        result = {}
        if "gen" in phases:
            result["test_cases"] = runner.gen()
        if "eval" in phases:
            # 如果 gen 阶段未执行，先 gen 获取测试用例
            tc = result.get("test_cases") or runner.gen()
            result["results"] = runner.eval(tc)
        if "report" in phases:
            # 如果 eval 阶段未执行，先 eval（传入空列表以触发加载已有结果）
            r = result.get("results") or runner.eval([])
            result["report"] = runner.report(r)
        return result
