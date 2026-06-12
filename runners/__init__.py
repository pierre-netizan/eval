# runners init — 注册所有可用 runner
from .direct_runner import DirectRunner
from .promptfoo_runner import PromptfooRunner
from lib.registry import RunnerRegistry

RunnerRegistry.register("direct", DirectRunner)
RunnerRegistry.register("promptfoo", PromptfooRunner)
