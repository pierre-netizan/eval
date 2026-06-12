"""Shared report utilities."""


def calc_stats(results: list) -> dict:
    """Aggregate results into stats dict."""
    total = len(results)
    if total == 0:
        return {"total": 0, "blocked": 0, "bypassed": 0, "block_rate": 0.0}

    blocked = sum(1 for r in results if r.get("blocked_by_arsguard"))
    bypassed = total - blocked
    judged_blocked = sum(1 for r in results if r.get("judge_verdict") == "BLOCKED")
    judge_consensus = sum(
        1 for r in results
        if r["blocked_by_arsguard"] == (r.get("judge_verdict") == "BLOCKED")
    )

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

    return {
        "total": total,
        "blocked": blocked,
        "bypassed": bypassed,
        "block_rate": blocked / total * 100 if total else 0,
        "judged_blocked": judged_blocked,
        "judge_consensus": judge_consensus,
        "judge_consensus_rate": judge_consensus / total * 100 if total else 0,
        "by_category": cat_stats,
    }
