#!/usr/bin/env python3
"""4-Cycle arsguard interception test with structured logging and extensible tool support.

Cycles (in order):
  1. promptfoo-only   — N random attacks from promptfoo payloads
  2. asb-only         — N random attacks from ASB payloads
  3. hackmyagent-only — N random attacks from HackMyAgent payloads
  4. joint            — N random attacks from ALL registered tools (extensible)

Output layout (<output_dir>/<cycle>/):
  gen/gen_attacks.json  gen_report.json
  eval/eval_results.json  eval_report.json
  report/report.{md,html,tex,pdf}
  logs/<cycle>.log  (optional combined log)

Log format (STRUCTURED — every entry has all six mandatory fields):
  time|tool|model|file|function|line|message

Adding new tools:
  1. Create runners/<name>_runner.py exporting PAYLOADS + NAMES dicts
  2. Import them below and add to ALL_TOOLS — joint cycle picks them up automatically
"""

import argparse
import json
import os
import random
import sys
import time
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "arsguard", "src"))

from lib.log_utils import ToolLogger
from lib.reporter import calc_stats, gen_metadata, eval_metadata, save_json
from report.generate_report import save_reports

# --- Tool payload imports ---
# To add a new tool: import PAYLOADS + NAMES here, then add to ALL_TOOLS dict
from runners.hackmyagent_runner import HACKMYAGENT_PAYLOADS, HACKMYAGENT_NAMES
from runners.asb_runner import ASB_PAYLOADS, ASB_NAMES
from runners.promptfoo_runner import PROMPTFOO_PAYLOADS, PROMPTFOO_NAMES

# ALL_TOOLS is THE EXTENSIBLE REGISTRY. Joint cycle uses ALL tools.
# Add new entries here when creating new runners.
ALL_TOOLS = {
    "promptfoo": (PROMPTFOO_PAYLOADS, PROMPTFOO_NAMES),
    "asb": (ASB_PAYLOADS, ASB_NAMES),
    "hackmyagent": (HACKMYAGENT_PAYLOADS, HACKMYAGENT_NAMES),
}


def collect_payloads(tools=None):
    """Flatten all payloads from the given tool set into a list of attack dicts.

    Each dict contains prompt, category, category_name, tool, and optional
    subcategory fields. Returns an empty list if tools is empty or None.
    """
    items = []
    if tools is None:
        return items
    for tool_name, (payloads, names) in tools.items():
        for cat_id, prompts in payloads.items():
            for p in prompts:
                # Payloads may be plain strings (for simple attacks) or dicts
                # (with subcategory metadata from newer runners)
                if isinstance(p, dict):
                    prompt_text = p["prompt"]
                    subcat = p.get("subcategory", "")
                    subcat_name = p.get("subcategory_name", "")
                else:
                    prompt_text = p
                    subcat = ""
                    subcat_name = ""
                items.append({
                    "prompt": prompt_text,
                    "category": cat_id,
                    "category_name": names.get(cat_id, cat_id),
                    "tool": tool_name,
                    "tool_subcategory": subcat,
                    "tool_subcategory_name": subcat_name,
                })
    return items


def sample_attacks(pool, n):
    """Sample N attacks from pool via uniform random selection (with replacement).

    Falls back to returning the entire pool (shuffled, truncated) if pool is
    smaller than N.
    """
    if not pool:
        return []
    k = min(n, len(pool))
    # Use random.sample for exact subset (no repeats), fall back to
    # random.choices (with replacement) when pool is too small
    return random.sample(pool, k) if k < len(pool) else random.choices(pool, k=n)


def import_hook(category_id):
    """Dynamically import an arsguard hook class by category ID.

    Uses __import__ with fromlist to import the specific class from the
    plugin's hooks submodule. This avoids needing a central registry and
    allows each hook to be loaded on demand.
    """
    mapping = {
        "llm01_prompt_injection": ("plugins.hooks.llm01_prompt_injection", "PromptInjectionHook"),
        "llm02_insecure_output": ("plugins.hooks.llm02_insecure_output", "InsecureOutputHook"),
        "llm03_training_data_poisoning": ("plugins.hooks.llm03_training_data_poisoning", "TrainingDataPoisoningHook"),
        "llm04_model_dos": ("plugins.hooks.llm04_model_dos", "ModelDosHook"),
        "llm05_supply_chain": ("plugins.hooks.llm05_supply_chain", "SupplyChainHook"),
        "llm06_sensitive_info": ("plugins.hooks.llm06_sensitive_info", "SensitiveInfoHook"),
        "llm07_insecure_plugin": ("plugins.hooks.llm07_insecure_plugin", "InsecurePluginHook"),
        "llm08_excessive_agency": ("plugins.hooks.llm08_excessive_agency", "ExcessiveAgencyHook"),
        "llm09_overreliance": ("plugins.hooks.llm09_overreliance", "OverrelianceHook"),
        "llm10_model_theft": ("plugins.hooks.llm10_model_theft", "ModelTheftHook"),
    }
    mod_path, cls_name = mapping[category_id]
    mod = __import__(mod_path, fromlist=[cls_name])
    return getattr(mod, cls_name)


def get_hook_config(category_id):
    """Return configuration dict for the given hook category."""
    base = {"enabled": True, "action": "block", "severity": "high"}
    configs = {
        "llm01_prompt_injection": {**base},
        "llm02_insecure_output": {**base, "filter_patterns": [
            "password.*:", "api_key.*:", "secret.*:", "token.*:",
            "credit_card", "ssn", "ssh-.*key",
        ]},
        "llm03_training_data_poisoning": {**base, "max_training_samples": 100, "anomaly_threshold": 0.3},
        "llm04_model_dos": {**base, "rate_limit": {"requests_per_minute": 30, "requests_per_hour": 500, "concurrency_limit": 5, "token_per_minute": 100000}},
        "llm05_supply_chain": {**base, "action": "block", "allowed_sources": ["pypi.org", "github.com/opencode-ai"], "block_unknown_sources": True},
        "llm06_sensitive_info": {**base, "masking": True},
        "llm07_insecure_plugin": {**base, "allowed_plugins": ["arsguard.*"], "block_network_access": True, "max_memory_mb": 512},
        "llm08_excessive_agency": {**base, "max_allowed_actions": 10, "allowed_domains": ["api.openclaw.ai"], "block_exec_command": True, "block_file_write": True},
        "llm09_overreliance": {**base, "action": "block", "min_confidence": 0.4, "require_citation": False, "max_retries": 3},
        "llm10_model_theft": {**base, "extract_protection": True, "max_batch_size": 10, "max_requests_per_session": 100, "detect_parallel_extraction": True},
    }
    return configs.get(category_id, base)


def test_attack(cat_id, attack_text, hook):
    """Run a single attack through hook.inspect_request + inspect_response.

    A two-phase inspection is used: the hook first inspects the *request* for
    malicious input patterns. If no match is found, it falls back to inspecting
    the *response* for unsafe output content. Either phase can flag the attack.

    Returns (blocked: bool, hook_result: HookResult or None).
    """
    request = {"prompt": attack_text, "messages": [{"role": "user", "content": attack_text}]}
    response = {"response": attack_text, "text": attack_text}
    result = hook.inspect_request(request)
    # Only check response if request didn't trigger a block
    if result is None:
        result = hook.inspect_response(response)
    blocked = result is not None and result.should_block()
    return blocked, result


def run_eval(attacks, log, model="qwen3-0.6b"):
    """Run all attacks through the corresponding arsguard hooks.

    Logs every attack with the structured format. Returns the results list.
    Hooks are cached per category to avoid repeated import + instantiation overhead.
    """
    hook_cache = {}
    results = []
    total = len(attacks)
    t_start = time.time()

    for i, atk in enumerate(attacks):
        cat = atk["category"]
        prompt = atk["prompt"]

        # Cache hooks by category so we don't re-instantiate for every attack
        if cat not in hook_cache:
            HookClass = import_hook(cat)
            cfg = get_hook_config(cat)
            hook_cache[cat] = HookClass(cfg)
        hook = hook_cache[cat]

        blocked, hook_result = test_attack(cat, prompt, hook)

        # Determine blocking hook name and short match detail for logging
        hook_name = hook.name if hasattr(hook, "name") else cat
        if blocked:
            detail = hook_result.reason[:120] if hook_result else "blocked"
            log.result(i + 1, total,
                       f"{atk['tool']}/{atk.get('tool_subcategory_name', '?')}",
                       "blocked", hook_name, detail)
        else:
            log.result(i + 1, total,
                       f"{atk['tool']}/{atk.get('tool_subcategory_name', '?')}",
                       "bypassed", hook_name, "no pattern matched")

        # Build standardised result dict for downstream reporting
        r = {
            "category": cat,
            "category_name": atk.get("category_name", cat),
            "prompt": prompt,
            "blocked_by_arsguard": blocked,
            "judge_verdict": "BLOCKED" if blocked else "BYPASSED",
            "judge_raw": str(hook_result) if hook_result else "no match",
            "response": str(hook_result)[:200] if hook_result else "passed through",
            "tool": atk.get("tool", ""),
            "tool_id": f"{cat}-{atk.get('tool', '?')}-{i+1:04d}",
            "tool_subcategory": atk.get("tool_subcategory", ""),
            "tool_subcategory_name": atk.get("tool_subcategory_name", ""),
            "blocking_hook": hook_name if blocked else "",
        }
        results.append(r)

    elapsed = time.time() - t_start
    log.info(f"Evaluation complete: {total} attacks in {elapsed:.1f}s ({total/elapsed:.0f} attacks/s)")
    return results


def save_cycle(cycle_dir, attacks, results, log):
    """Save gen + eval + report into <cycle_dir>/gen/, eval/, report/.

    Each cycle gets its own directory tree under the output root:
      <cycle_dir>/gen/     — generated attack payloads + metadata
      <cycle_dir>/eval/    — per-attack eval results + summary
      <cycle_dir>/report/  — rendered reports (md, html, tex, pdf)
    """
    gen_dir = os.path.join(cycle_dir, "gen")
    eval_dir = os.path.join(cycle_dir, "eval")
    report_dir = os.path.join(cycle_dir, "report")
    for d in (gen_dir, eval_dir, report_dir):
        os.makedirs(d, exist_ok=True)

    # Gen phase output: attack payloads and generation metadata
    ga_path = os.path.join(gen_dir, "gen_attacks.json")
    with open(ga_path, "w") as f:
        json.dump(attacks, f, ensure_ascii=False, indent=2)
    gen_meta = gen_metadata(attacks, {"runner": os.path.basename(cycle_dir)})
    save_json(gen_meta, os.path.join(gen_dir, "gen_report.json"))
    log.info(f"Generated {len(attacks)} attacks → {gen_dir}")

    # Eval phase output: per-attack blocking results and summary
    er_path = os.path.join(eval_dir, "eval_results.json")
    with open(er_path, "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    eval_meta = eval_metadata(results, {"runner": os.path.basename(cycle_dir)})
    save_json(eval_meta, os.path.join(eval_dir, "eval_report.json"))
    log.info(f"Evaluated {len(results)} attacks → {eval_dir}")

    # Report phase output: rendered documents in multiple formats
    save_reports(results, output_dir=report_dir, compile_pdf=True,
                 filename_prefix="report", tool_label=os.path.basename(cycle_dir))
    log.info(f"Reports generated → {report_dir}")

    stats = calc_stats(results)
    return stats


def make_cycles(cycle_arg):
    """Build the list of (cycle_name, tool_subset) tuples to execute.

    The cycle order is always: promptfoo → asb → hackmyagent → joint.
    This guarantees consistent output and allows easy addition of new tools
    to the joint cycle by simply adding entries to ALL_TOOLS.
    """
    # Define the three single-tool cycles; each uses only its own payloads
    single_cycles = [
        ("promptfoo", {"promptfoo": ALL_TOOLS["promptfoo"]}),
        ("asb", {"asb": ALL_TOOLS["asb"]}),
        ("hackmyagent", {"hackmyagent": ALL_TOOLS["hackmyagent"]}),
    ]
    if cycle_arg == "all":
        # Run singles first, then the joint cycle that combines ALL tools
        return single_cycles + [("joint", ALL_TOOLS)]
    if cycle_arg == "joint":
        return [("joint", ALL_TOOLS)]
    # Single tool cycle — look up the matching entry
    for name, _ in single_cycles:
        if name == cycle_arg:
            return [(cycle_arg, {cycle_arg: ALL_TOOLS[cycle_arg]})]
    raise ValueError(f"Unknown cycle '{cycle_arg}'. Valid: promptfoo, asb, hackmyagent, joint, all")


def main():
    parser = argparse.ArgumentParser(description="4-Cycle arsguard interception test")
    parser.add_argument("--n", type=int, default=1000, help="Attacks per cycle (default: 1000)")
    parser.add_argument("--cycle", choices=["promptfoo", "asb", "hackmyagent", "joint", "all"],
                        default="all", help="Cycle to run (default: all 4)")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for reproducibility")
    parser.add_argument("--output", type=str, default=None, help="Output directory (default: <proj_root>/data-results/current/)")
    parser.add_argument("--model", type=str, default="qwen3-0.6b", help="Model name for logging")
    args = parser.parse_args()

    # Determine output root directory — user override or default to <proj_root>/data-results/current/
    if args.output:
        output_root = os.path.abspath(args.output)
    else:
        # Default: project root / data-results/current/
        output_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data-results", "current"))

    # Create logs directory for per-cycle and combined log files
    log_dir = os.path.join(output_root, "logs")
    os.makedirs(log_dir, exist_ok=True)

    # Seed for reproducible random attack selection
    if args.seed is not None:
        random.seed(args.seed)

    # Setup global logger — writes to both console and combined log file
    log = ToolLogger("cycle", model=args.model)
    combined_log_path = os.path.join(log_dir, "cycle_combined.log")
    log.add_file_handler(combined_log_path)
    log.info(f"Starting 4-cycle test — output={output_root}, n={args.n}, seed={args.seed}")

    # Determine cycles to run (promptfoo, asb, hackmyagent, joint, or all)
    cycles = make_cycles(args.cycle)
    log.info(f"Cycles: {[c[0] for c in cycles]}")

    t_total = time.time()

    for cycle_name, tool_set in cycles:
        log.info(f"=== Cycle: {cycle_name} ({args.n} attacks) ===")
        t_cycle = time.time()
        cycle_dir = os.path.join(output_root, cycle_name)

        # Per-cycle logger (logs to both combined file and per-cycle file)
        cl = ToolLogger(cycle_name, model=args.model)
        cycle_log_path = os.path.join(log_dir, f"{cycle_name}.log")
        cl.add_file_handler(cycle_log_path)
        cl.add_file_handler(combined_log_path)
        cl.info(f"Starting cycle — {args.n} attacks, tools={list(tool_set.keys())}")

        # Generate random attacks by flattening tool payloads then sampling
        pool = collect_payloads(tool_set)
        cl.info(f"Collected {len(pool)} unique payloads from {len(tool_set)} tool(s)")
        attacks = sample_attacks(pool, args.n)
        cl.info(f"Sampled {len(attacks)} attacks")

        # Evaluate each attack against the corresponding arsguard hook
        results = run_eval(attacks, cl, model=args.model)

        # Save gen/eval/report data to cycle-specific directories
        stats = save_cycle(cycle_dir, attacks, results, cl)

        elapsed = time.time() - t_cycle
        cl.info(f"Cycle complete — {stats['blocked']}/{stats['total']} blocked "
                f"({stats['block_rate']:.1f}%) in {elapsed:.1f}s")

        # Print human-readable summary to stdout
        print(f"\n  {cycle_name} results ({elapsed:.1f}s):")
        print(f"    Total:   {stats['total']}")
        print(f"    Blocked: {stats['blocked']} ({stats['block_rate']:.1f}%)")
        print(f"    Bypassed: {stats['bypassed']}")
        by_cat = stats.get("by_category", {})
        for c, s in sorted(by_cat.items()):
            print(f"      {s['name']:40s} {s['blocked']:3d}/{s['total']:3d} ({s['block_rate']:.0f}%)")

    total_elapsed = time.time() - t_total
    print(f"\n{'=' * 50}")
    print(f"  All cycles complete in {total_elapsed:.1f}s")
    print(f"  Output: {output_root}/<cycle>/  (gen/  eval/  report/)")
    print(f"  Logs:   {log_dir}/")
    print(f"{'=' * 50}")

    log.info(f"All cycles complete — total {total_elapsed:.1f}s")


if __name__ == "__main__":
    main()
