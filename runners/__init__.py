"""runners package — registers all available test runners.

Runner implementations:
  - DirectRunner:      Full gen/eval/report pipeline using Python (no external deps).
  - PromptfooRunner:   Payloads formatted for the promptfoo CLI runner.
  - HackmyagentRunner: Payloads following the HackMyAgent attack methodology.
  - AsbRunner:         Payloads following the ASB (DPI/OPI/MP/PoT) methodology.

Each runner is registered into RunnerRegistry by its string key so the
test harness can instantiate the correct runner from config at runtime.
"""

from .direct_runner import DirectRunner
from .promptfoo_runner import PromptfooRunner
from .hackmyagent_runner import HackmyagentRunner
from .asb_runner import AsbRunner
from lib.registry import RunnerRegistry

RunnerRegistry.register("direct", DirectRunner)
RunnerRegistry.register("promptfoo", PromptfooRunner)
RunnerRegistry.register("hackmyagent", HackmyagentRunner)
RunnerRegistry.register("asb", AsbRunner)
