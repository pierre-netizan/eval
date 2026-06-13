#!/usr/bin/env python3
"""Main entry point for the arsguard-eval evaluation pipeline.

Orchestrates the three-phase pipeline (Gen -> Eval -> Report) by delegating
to a pluggable Runner (direct or promptfoo) via RunnerRegistry.

Usage:
    python3 eval/scripts/run.py [--runner direct|promptfoo] [--phase gen|eval|report|all] [options]

Examples:
    python3 eval/scripts/run.py --runner direct --phase all
    python3 eval/scripts/run.py --runner promptfoo --phase eval --verbose
"""

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import yaml
from lib.registry import RunnerRegistry
import runners  # noqa: F401 — registers runners on import


def load_config(path: str = None) -> dict:
    """Load eval configuration from a YAML file.

    Falls back to a default config dict if the file is missing.
    The config path defaults to <script_dir>/../config/eval.yaml.

    Args:
        path: Absolute or relative path to the YAML config file. None uses default.

    Returns:
        Parsed config dict, or a minimal default if the file does not exist.
    """
    if path is None:
        path = os.path.join(os.path.dirname(__file__), "..", "config", "eval.yaml")
    if not os.path.exists(path):
        print(f"[eval] Config not found: {path}", file=sys.stderr)
        return {"runner": "direct", "output_dir": "data"}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def main():
    """Parse CLI args, load config, and dispatch the requested pipeline phase(s).

    Supports a --runner override, --phase selection, and optional --verbose flag.
    Delegates actual execution to the runner registered in RunnerRegistry.
    """
    parser = argparse.ArgumentParser(description="arsguard-eval pipeline")
    parser.add_argument("--runner", "-r", default=None, help="Runner to use")
    parser.add_argument("--phase", "-p", default="all",
                        choices=["gen", "eval", "report", "all"],
                        help="Phase to run")
    parser.add_argument("--config", "-c", default=None, help="Config file path")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    config = load_config(args.config)
    # Allow --config to specify the top-level file, but also support nested "eval" key
    eval_cfg = config.get("eval", config)
    if args.runner:
        eval_cfg["runner"] = args.runner
    if args.verbose:
        eval_cfg["verbose"] = True

    runner_name = eval_cfg.get("runner", "direct")
    print(f"[eval] Runner: {runner_name}")

    try:
        result = RunnerRegistry.run(runner_name, eval_cfg,
                                    phases=None if args.phase == "all" else [args.phase])
    except KeyError as e:
        print(f"[eval] {e}", file=sys.stderr)
        sys.exit(1)

    # Print the report output to stdout when running report phase
    if args.phase in ("all", "report") and "report" in result:
        print("\n" + result["report"])


if __name__ == "__main__":
    main()
