#!/usr/bin/env python3
"""Comprehensive test: runs all tools against improved arsguard hooks.

Tests each tool individually (hackmyagent, asb, promptfoo) and all tools combined.
Generates n+1 reports (per-tool + all) in all formats (md/html/tex/pdf).

Pipeline phases:
   1. Gen   — convert raw payloads into standardised attack dicts
   2. Eval  — test each attack against the corresponding arsguard hook
   3. Report — render per-tool + combined reports in multiple output formats

Usage:
    python3 eval/scripts/test_comprehensive.py [--tool <name>]
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "arsguard", "src"))

from lib.reporter import calc_stats, gen_metadata, eval_metadata, save_json
from report.generate_report import save_reports, save_all_reports
from runners.hackmyagent_runner import HACKMYAGENT_PAYLOADS, HACKMYAGENT_NAMES
from runners.asb_runner import ASB_PAYLOADS, ASB_NAMES
from runners.promptfoo_runner import PROMPTFOO_PAYLOADS, PROMPTFOO_NAMES

# All output lands under eval/data/
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Human-readable names for all 10 OWASP categories
CAT_NAMES = {
    "llm01_prompt_injection": "LLM01: Prompt Injection",
    "llm02_insecure_output": "LLM02: Insecure Output Handling",
    "llm03_training_data_poisoning": "LLM03: Training Data Poisoning",
    "llm04_model_dos": "LLM04: Model Denial of Service",
    "llm05_supply_chain": "LLM05: Supply Chain Vulnerabilities",
    "llm06_sensitive_info": "LLM06: Sensitive Information Disclosure",
    "llm07_insecure_plugin": "LLM07: Insecure Plugin Design",
    "llm08_excessive_agency": "LLM08: Excessive Agency",
    "llm09_overreliance": "LLM09: Overreliance",
    "llm10_model_theft": "LLM10: Model Theft",
}


def import_hook(category_id):
    """Dynamically import an arsguard hook class by OWASP category ID.

    Uses __import__ with fromlist to load the specific hook class from
    the plugins.hooks submodule, avoiding a central registry.

    Args:
        category_id: One of the llmXX_* category identifiers.

    Returns:
        The hook class (not an instance), ready for instantiation.
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
    """Return the configuration dict for a given hook category.

    Each hook receives category-specific tuning parameters (patterns,
    rate limits, allowed sources, etc.) while inheriting sensible defaults.

    Args:
        category_id: The OWASP category identifier.

    Returns:
        A dict of configuration values for the hook constructor.
    """
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

    Two-phase inspection: request is checked first; if no match, response
    is checked. Either phase can flag the attack as blocked.

    Args:
        cat_id: OWASP category ID.
        attack_text: The attack prompt string.
        hook: An instantiated arsguard hook object.

    Returns:
        (blocked: bool, hook_result: HookResult or None)
    """
    request = {"prompt": attack_text, "messages": [{"role": "user", "content": attack_text}]}
    response = {"response": attack_text, "text": attack_text}
    result = hook.inspect_request(request)
    # Fall back to response inspection only if request didn't trigger
    if result is None:
        result = hook.inspect_response(response)
    blocked = result is not None and result.should_block()
    return blocked, result


def run_tool(name, attack_dict, names_dict):
    """Run all attacks for a single tool and print results.

    Iterates over categories then individual attacks, instantiating the
    appropriate hook for each category. Prints a status line per attack.

    Args:
        name: Tool name (hackmyagent, asb, promptfoo).
        attack_dict: {category_id: [attack_strings_or_dicts]}.
        names_dict: {category_id: human_readable_name}.

    Returns:
        List of result dicts.
    """
    print(f"\n{'=' * 60}")
    print(f"  Tool: {name}")
    print(f"{'=' * 60}")
    results = []
    for cat_id, attacks in attack_dict.items():
        print(f"\n  \u2500\u2500 {names_dict.get(cat_id, cat_id)} \u2500\u2500")
        HookClass = import_hook(cat_id)
        cfg = get_hook_config(cat_id)
        hook = HookClass(cfg)
        for i, attack in enumerate(attacks, 1):
            # Handle both plain string and dict-with-metadata formats
            if isinstance(attack, dict):
                prompt_text = attack["prompt"]
                subcat = attack.get("subcategory", "")
                subcat_name = attack.get("subcategory_name", "")
            else:
                prompt_text = attack
                subcat = ""
                subcat_name = ""
            blocked, hook_result = test_attack(cat_id, prompt_text, hook)
            r = {
                "category": cat_id,
                "category_name": names_dict.get(cat_id, cat_id),
                "prompt": prompt_text,
                "blocked_by_arsguard": blocked,
                "judge_verdict": "BLOCKED" if blocked else "BYPASSED",
                "judge_raw": str(hook_result) if hook_result else "no match",
                "response": str(hook_result)[:200] if hook_result else "passed through",
                "tool": name,
                "tool_id": f"{cat_id}-{name}-{i:03d}",
                "tool_subcategory": subcat,
                "tool_subcategory_name": subcat_name,
            }
            results.append(r)
            # Short symbol key for compact tool identification in output
            symbols = {"hackmyagent": "hma", "asb": "asb", "direct": "dir", "promptfoo": "pf"}
            sym = symbols.get(name, "?")
            status = "\u2713" if blocked else "\u2717"
            print(f"    [{sym}{i:03d}] {status} {prompt_text[:60]}")
    return results


def print_stats(results, label):
    """Print a summary line with total/blocked/rate for a result set."""
    total = len(results)
    blocked = sum(1 for r in results if r["blocked_by_arsguard"])
    rate = blocked / total * 100 if total else 0
    print(f"\n  {label}: {blocked}/{total} \u62e6\u622a ({rate:.1f}%)")


def save_phase_data(results, tool_name, phase):
    """Save per-phase metadata JSON (gen or eval) for a given tool.

    Args:
        results: List of attack or result dicts.
        tool_name: Identifier used in the filename.
        phase: "gen" or "eval".

    Returns:
        The filename that was written.
    """
    cfg = {"runner": tool_name}
    if phase == "gen":
        meta = gen_metadata(results, cfg)
    else:
        meta = eval_metadata(results, cfg)
    fname = f"{phase}_report_{tool_name}.json"
    save_json(meta, os.path.join(OUTPUT_DIR, fname))
    return fname


def generate_attacks(name, payloads, nnames):
    """Generate attack dicts from payloads (handles str or dict format).

    Each payload entry may be a plain string (legacy format) or a dict with
    optional subcategory metadata (newer runner format).

    Args:
        name: Tool name.
        payloads: {category_id: [prompt_strings_or_dicts]}.
        nnames: {category_id: human_readable_name}.

    Returns:
        List of standardised attack dicts.
    """
    attacks = []
    for cat_id, prompts in payloads.items():
        for i, p in enumerate(prompts, 1):
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
                "category_name": nnames.get(cat_id, cat_id),
                "prompt": prompt_text,
                "tool": name,
                "tool_subcategory": subcat,
                "tool_subcategory_name": subcat_name,
                "tool_id": f"{cat_id}-{name}-{i:03d}",
            })
    return attacks


def run_phase_gen(name, payloads, nnames):
    """Gen phase for a single tool: convert payloads to attack dicts and save.

    Args:
        name: Tool name.
        payloads: {category_id: [prompt_strings_or_dicts]}.
        nnames: {category_id: human_readable_name}.

    Returns:
        List of generated attack dicts.
    """
    attacks = generate_attacks(name, payloads, nnames)
    attack_file = os.path.join(OUTPUT_DIR, f"gen_attacks_{name}.json")
    with open(attack_file, "w") as f:
        json.dump(attacks, f, ensure_ascii=False, indent=2)
    fname = save_phase_data(attacks, name, "gen")
    print(f"  {name}: {len(attacks)} attacks -> {fname}")
    return attacks


def run_phase_eval(name, payloads, nnames):
    """Eval phase for a single tool: test all attacks and save results.

    Args:
        name: Tool name.
        payloads: {category_id: [attack_strings_or_dicts]}.
        nnames: {category_id: human_readable_name}.

    Returns:
        List of eval result dicts.
    """
    results = run_tool(name, payloads, nnames)
    fname = save_phase_data(results, name, "eval")
    print_stats(results, f"{name} intercept")
    with open(os.path.join(OUTPUT_DIR, f"eval_results_{name}.json"), "w") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"  -> data/eval_results_{name}.json")
    return results


def run_phase_report(name, results):
    """Report phase for a single tool: generate all report formats.

    Args:
        name: Tool name (used in filenames).
        results: List of eval result dicts.
    """
    from report.generate_report import save_reports
    paths = save_reports(results, output_dir=OUTPUT_DIR, compile_pdf=True,
                         filename_prefix=f"report_{name}", tool_label=name)
    print(f"  {name}:")
    for fmt, p in paths.items():
        print(f"    [{fmt}] {p}")


def main():
    """Run the comprehensive test pipeline: Gen -> Eval -> Report.

    Supports a --tool flag to run a single tool in isolation.
    When all tools are run, produces combined results and reports too.
    """
    import argparse
    parser = argparse.ArgumentParser(description="Comprehensive arsguard test suite")
    parser.add_argument("--tool", "-t", default=None, help="Run only this tool (hackmyagent, asb, promptfoo)")
    args = parser.parse_args()

    tools = {
        "hackmyagent": (HACKMYAGENT_PAYLOADS, HACKMYAGENT_NAMES),
        "asb": (ASB_PAYLOADS, ASB_NAMES),
        "promptfoo": (PROMPTFOO_PAYLOADS, PROMPTFOO_NAMES),
    }

    if args.tool:
        if args.tool not in tools:
            print(f"Unknown tool: {args.tool}. Available: {list(tools.keys())}")
            sys.exit(1)
        tools = {args.tool: tools[args.tool]}

    all_results = []
    per_tool_results = {}

    # Phase 1: Gen — convert raw payloads into standardised attack dicts per tool
    print("=" * 60)
    print("  Phase 1: Gen — Attack Generation")
    print("=" * 60)
    gen_attacks = {}
    for name, (payloads, nnames) in tools.items():
        attacks = run_phase_gen(name, payloads, nnames)
        gen_attacks[name] = attacks

    # Phase 2: Eval — test each tool's attacks against arsguard hooks
    print(f"\n{'=' * 60}")
    print("  Phase 2: Eval — Per-Tool Testing")
    print("=" * 60)
    for name, (payloads, nnames) in tools.items():
        results = run_phase_eval(name, payloads, nnames)
        per_tool_results[name] = results
        all_results.extend(results)

    if len(tools) > 1:
        # Only do combined analysis when running all tools
        print(f"\n{'=' * 60}")
        print("  Phase 3: All Tools Combined")
        print("=" * 60)
        cfg_all = {"runner": "all"}
        eval_meta = eval_metadata(all_results, cfg_all)
        save_json(eval_meta, os.path.join(OUTPUT_DIR, "eval_report_all.json"))
        with open(os.path.join(OUTPUT_DIR, "eval_results_all.json"), "w") as f:
            json.dump(all_results, f, ensure_ascii=False, indent=2)
        print_stats(all_results, "All tools combined")

        # Per-tool summary across all categories
        print("\n  Per-tool summary:")
        for name, results in per_tool_results.items():
            total = len(results)
            blocked = sum(1 for r in results if r["blocked_by_arsguard"])
            print(f"    {name:15s}: {blocked:3d}/{total:3d} ({blocked/total*100:.1f}%)")

        # Per-category summary across all tools
        print("\n  Per-category summary (all tools):")
        by_cat = {}
        for r in all_results:
            cat = r["category"]
            by_cat.setdefault(cat, {"total": 0, "blocked": 0})
            by_cat[cat]["total"] += 1
            if r["blocked_by_arsguard"]:
                by_cat[cat]["blocked"] += 1
        for cat, s in sorted(by_cat.items()):
            print(f"    {cat:35s}: {s['blocked']:3d}/{s['total']:3d} ({s['blocked']/s['total']*100:.1f}%)")

    # Phase 4: Report — generate per-tool reports in all formats
    print(f"\n{'=' * 60}")
    print("  Phase 4: Report — Per-Tool Reports")
    print("=" * 60)
    for name, results in per_tool_results.items():
        run_phase_report(name, results)

    # Combined report if multi-tool (Phase 5)
    if len(tools) > 1:
        print(f"\n{'=' * 60}")
        print("  Phase 5: Combined Report")
        print("=" * 60)
        all_paths = save_all_reports(per_tool_results, all_results, output_dir=OUTPUT_DIR, compile_pdf=True)

    # Final summary: list all output files and overall blocking statistics
    print(f"\n  data/ directory files:")
    for fname in sorted(os.listdir(OUTPUT_DIR)):
        if fname.startswith("."):
            continue
        fpath = os.path.join(OUTPUT_DIR, fname)
        if os.path.isfile(fpath):
            print(f"    {fname:35s} {os.path.getsize(fpath):>8,} bytes")

    total_all = len(all_results)
    blocked_all = sum(1 for r in all_results if r['blocked_by_arsguard'])
    print(f"\n{'=' * 60}")
    print(f"  Total: {total_all} attacks | "
          f"{blocked_all} blocked | "
          f"{total_all - blocked_all} bypassed | "
          f"Rate: {blocked_all/total_all*100:.1f}%")
    print(f"  Reports: md / html / tex / pdf x {len(per_tool_results) + 1} (per-tool + all)")
    print("=" * 60)


if __name__ == "__main__":
    main()
