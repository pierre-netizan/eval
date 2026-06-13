"""Reporter — 统计计算和报告生成工具函数。

Statistics calculation and report generation utility functions.
提供测试结果聚合、按类别分组统计、各阶段元数据生成、JSON 存储等功能。
"""

import json
import os
from datetime import datetime


def calc_stats(results: list) -> dict:
    """聚合测试结果生成统计指标 / Aggregate test results into statistics.

    计算全局统计（总数/拦截数/绕过数/拦截率/法官共识率），
    并按 OWASP 类别和 (tool, subcategory) 分组计算详细指标。

    Args:
        results: eval() 返回的测试结果列表。List of test result dicts.

    Returns:
        dict: 包含以下键的统计字典 / Stats dict with keys:
            total, blocked, bypassed, block_rate,
            judged_blocked, judge_consensus, judge_consensus_rate,
            by_category (dict of per-category stats),
            by_subcategory (dict of per-tool-subcategory stats)
    """
    total = len(results)
    # 空结果集时返回零值
    if total == 0:
        return {"total": 0, "blocked": 0, "bypassed": 0, "block_rate": 0.0}

    # 统计 arsguard 实际拦截数
    blocked = sum(1 for r in results if r.get("blocked_by_arsguard"))
    bypassed = total - blocked
    # 统计法官判定拦截数
    judged_blocked = sum(1 for r in results if r.get("judge_verdict") == "BLOCKED")
    # 统计 arsguard 拦截与法官判定一致的数量（共识）
    judge_consensus = sum(
        1 for r in results
        if r["blocked_by_arsguard"] == (r.get("judge_verdict") == "BLOCKED")
    )

    # 按 OWASP 类别分组统计 (e.g., LLM01, LLM02, ...)
    by_category = {}
    for r in results:
        cat = r.get("category", "unknown")
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(r)

    cat_stats = {}
    for cat, items in sorted(by_category.items()):
        cat_total = len(items)
        cat_blocked = sum(1 for i in items if i["blocked_by_arsguard"])
        cat_consensus = sum(
            1 for i in items
            if i["blocked_by_arsguard"] == (i.get("judge_verdict") == "BLOCKED")
        )
        cat_stats[cat] = {
            "name": items[0].get("category_name", cat),
            "total": cat_total,
            "blocked": cat_blocked,
            "block_rate": cat_blocked / cat_total * 100 if cat_total else 0,
            "consensus": cat_consensus,
            "consensus_rate": cat_consensus / cat_total * 100 if cat_total else 0,
        }

    # 按 (tool, subcategory) 二级分组统计
    by_tool_subcat = {}
    for r in results:
        tool = r.get("tool", "")
        subcat = r.get("tool_subcategory", "")
        key = (tool, subcat)
        if key not in by_tool_subcat:
            by_tool_subcat[key] = []
        by_tool_subcat[key].append(r)

    subcat_stats = {}
    for (tool, subcat), items in sorted(by_tool_subcat.items()):
        sc_total = len(items)
        sc_blocked = sum(1 for i in items if i["blocked_by_arsguard"])
        sc_name = items[0].get("tool_subcategory_name", subcat) if subcat else "(none)"
        subcat_stats[f"{tool}/{subcat}"] = {
            "tool": tool,
            "subcategory": subcat,
            "subcategory_name": sc_name,
            "total": sc_total,
            "blocked": sc_blocked,
            "block_rate": sc_blocked / sc_total * 100 if sc_total else 0,
        }

    return {
        "total": total,
        "blocked": blocked,
        "bypassed": bypassed,
        "block_rate": blocked / total * 100 if total else 0,
        "judged_blocked": judged_blocked,
        "judge_consensus": judge_consensus,
        "judge_consensus_rate": judge_consensus / total * 100 if total else 0,
        "by_category": cat_stats,
        "by_subcategory": subcat_stats,
    }


def gen_metadata(attacks: list, config: dict) -> dict:
    """生成 gen 阶段的元数据报告 / Build gen phase metadata report.

    Args:
        attacks: gen() 生成的攻击测试用例列表。List of attack test cases from gen().
        config: 运行配置（包含 runner/ollama 等信息）。Run configuration dict.

    Returns:
        dict: 包含阶段/时间戳/runner/模型/总数/按类别统计的元数据。
              Metadata dict with phase, timestamp, runner, model, total, by-category stats.
    """
    # 按类别聚合：统计每个类别的总数和唯一 ID/名称
    by_cat = {}
    for a in attacks:
        cat = a.get("category", "unknown")
        by_cat.setdefault(cat, {"total": 0, "ids": set(), "names": set()})
        by_cat[cat]["total"] += 1
        by_cat[cat]["ids"].add(cat)
        by_cat[cat]["names"].add(a.get("category_name", cat))
    # 将 set 转换为标量值输出
    cat_summary = {}
    for cat, v in sorted(by_cat.items()):
        cat_summary[cat] = {"name": next(iter(v["names"])), "total": v["total"]}

    return {
        "phase": "gen",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "runner": config.get("runner", "direct"),
        "ollama": {
            "host": config.get("ollama", {}).get("host", "http://localhost:11434"),
            "prompt_model": config.get("ollama", {}).get("prompt_model", ""),
        },
        "total_attacks": len(attacks),
        "categories": cat_summary,
    }


def eval_metadata(results: list, config: dict) -> dict:
    """生成 eval 阶段的元数据报告 / Build eval phase metadata report.

    Args:
        results: eval() 返回的测试结果列表。List of test results from eval().
        config: 运行配置。Run configuration dict.

    Returns:
        dict: 包含阶段/时间戳/统计摘要的元数据。
              Metadata dict with phase, timestamp, and stats summary.
    """
    stats = calc_stats(results)
    return {
        "phase": "eval",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "runner": config.get("runner", "direct"),
        "total": stats["total"],
        "blocked": stats["blocked"],
        "bypassed": stats["bypassed"],
        "block_rate": round(stats["block_rate"], 1),
        "judged_blocked": stats["judged_blocked"],
        "judge_consensus_rate": round(stats["judge_consensus_rate"], 1),
        "by_category": stats["by_category"],
    }


def save_json(data: dict, path: str):
    """将字典保存为 JSON 文件（含 indent 和 ensure_ascii=False）。

    Save a dict to a JSON file with indentation and Unicode support.
    自动创建父目录。

    Args:
        data: 要保存的字典数据。Dict data to save.
        path: 输出文件路径。Output file path.
    """
    # 确保输出目录存在
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
