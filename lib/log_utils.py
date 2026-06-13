"""Standardized logging utility for arsguard-eval test framework.

Produces log entries in the format:
    time|tool|model|file|function|line|message

All six metadata fields are mandatory and auto-detected from the call stack.
Extensible for any number of tools — just pass a different tool name.

Usage:
    from lib.log_utils import ToolLogger
    log = ToolLogger("promptfoo")
    log.info("Starting evaluation")  # auto-fills file/func/line
    log.add_file_handler("data-bk1/logs/promptfoo.log")
"""

import inspect
import logging
import os
import sys
from datetime import datetime
from typing import Optional


class ToolLogger:
    """Logger that auto-injects time|tool|model|file|func|line metadata.

    Every log call captures the caller's source location from the call stack,
    so you never need to manually specify file/function/line.

    Attributes:
        tool:  Tool name (e.g. "promptfoo", "asb", "hackmyagent", "joint", "cycle")
        model: Model identifier (default: "qwen3-0.6b")
    """

    def __init__(self, tool: str, model: str = "qwen3-0.6b"):
        self.tool = tool
        self.model = model
        self._logger = logging.getLogger(f"arsguard.{tool}")
        self._logger.setLevel(logging.DEBUG)
        # Use a plain message formatter — all metadata is pre-formatted into the message.
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            handler.setLevel(logging.DEBUG)
            handler.setFormatter(logging.Formatter("%(message)s"))
            self._logger.addHandler(handler)
            self._logger.propagate = False

    def add_file_handler(self, log_path: str):
        """Append a file handler so logs go to both stdout and the given path."""
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(logging.Formatter("%(message)s"))
        self._logger.addHandler(fh)

    def _preformat(self, msg: str, offset: int = 0) -> str:
        """Build the log line:  time|tool|model|file|func|line|msg

        Walks up the call stack (offset frames) to find the real caller.
        """
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        frame = inspect.currentframe()
        # Walk up: our fram -> _preformat -> info/warn/error -> public caller
        for _ in range(3 + offset):
            if frame is None:
                break
            frame = frame.f_back
        fname = ""
        func = ""
        lineno = 0
        if frame:
            info = inspect.getframeinfo(frame)
            fname = os.path.relpath(info.filename, os.getcwd()) if os.getcwd() else info.filename
            func = info.function
            lineno = info.lineno
        return f"{ts}|{self.tool}|{self.model}|{fname}|{func}|{lineno}|{msg}"

    def debug(self, msg: str, *args, **kwargs):
        self._logger.debug(self._preformat(msg))

    def info(self, msg: str, *args, **kwargs):
        self._logger.info(self._preformat(msg))

    def warning(self, msg: str, *args, **kwargs):
        self._logger.warning(self._preformat(msg))

    def error(self, msg: str, *args, **kwargs):
        self._logger.error(self._preformat(msg))

    def critical(self, msg: str, *args, **kwargs):
        self._logger.critical(self._preformat(msg))

    def result(self, attack_num: int, total: int, subcat: str,
               verdict: str, hook: str = "", reason: str = ""):
        """Log a single attack evaluation result in compact form.

        Args:
            attack_num: Current attack number (1-based)
            total: Total attacks in this cycle
            subcat: tool/subcategory_name string
            verdict: "blocked" or "bypassed"
            hook: Name of the hook that fired (or "—")
            reason: Matching reason or "no pattern matched"
        """
        status = "BLOCK" if verdict == "blocked" else "BYPASS"
        hook_info = f" [{hook}]" if hook else ""
        self.info(f"[{attack_num}/{total}] {subcat}: [{status}]{hook_info} {reason}")
