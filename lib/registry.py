class RunnerRegistry:
    """Runner 注册中心。通过 register() 注册，run() 自动调度。"""

    _runners = {}

    @classmethod
    def register(cls, name: str, runner_cls):
        cls._runners[name] = runner_cls

    @classmethod
    def get(cls, name: str):
        if name not in cls._runners:
            available = ", ".join(cls._runners.keys())
            raise KeyError(f"Unknown runner: {name}. Available: {available}")
        return cls._runners[name]

    @classmethod
    def list(cls) -> list:
        return list(cls._runners.keys())

    @classmethod
    def run(cls, name: str, config: dict, phases: list = None):
        """便捷方法：按名字运行 runner。"""
        runner_cls = cls.get(name)
        runner = runner_cls(config)
        if phases is None:
            return runner.run_all()
        result = {}
        if "gen" in phases:
            result["test_cases"] = runner.gen()
        if "eval" in phases:
            tc = result.get("test_cases") or runner.gen()
            result["results"] = runner.eval(tc)
        if "report" in phases:
            r = result.get("results") or runner.eval([])
            result["report"] = runner.report(r)
        return result
