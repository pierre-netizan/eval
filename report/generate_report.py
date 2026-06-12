"""Report generator — renders Markdown test report from eval results."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.reporter import calc_stats


def render_report(results: list) -> str:
    """Render full test report from results list."""
    stats = calc_stats(results)

    lines = []
    lines.append("# arsguard 安全测试报告")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("")

    # Summary
    lines.append("## 总体统计")
    lines.append("")
    lines.append("| 指标 | 数值 |")
    lines.append("|------|------|")
    lines.append(f"| 总测试数 | {stats['total']} |")
    lines.append(f"| 拦截成功 (arsguard) | {stats['blocked']} |")
    lines.append(f"| 拦截失败 (bypassed) | {stats['bypassed']} |")
    lines.append(f"| 拦截率 | {stats['block_rate']:.1f}% |")
    lines.append(f"| Judge 判定拦截 | {stats['judged_blocked']} |")
    lines.append(f"| Judge 一致率 | {stats['judge_consensus_rate']:.1f}% |")
    lines.append("")

    # By category
    lines.append("## 按 OWASP 分类统计")
    lines.append("")
    lines.append("| 分类 | 测试数 | 拦截数 | 拦截率 | Judge 一致率 |")
    lines.append("|------|--------|--------|--------|-------------|")
    for cat, s in stats.get("by_category", {}).items():
        lines.append(f"| {s['name']} | {s['total']} | {s['blocked']} | {s['block_rate']:.0f}% | {s['consensus_rate']:.0f}% |")
    lines.append("")

    # Bypassed details
    lines.append("## 拦截失败详情 (Bypassed)")
    lines.append("")
    bypassed = [r for r in results if not r.get("blocked_by_arsguard")]
    if bypassed:
        for i, r in enumerate(bypassed, 1):
            lines.append(f"### {i}. {r.get('category_name', r.get('category', 'unknown'))}")
            lines.append("")
            lines.append(f"- **攻击提示**: `{r['prompt'][:200]}`")
            lines.append(f"- **响应**: `{r.get('response', 'N/A')[:200]}`")
            lines.append(f"- **Judge 判定**: {r.get('judge_verdict', 'N/A')}")
            lines.append("")
    else:
        lines.append("全部拦截成功！未发现绕过。")
        lines.append("")

    # Blocked summary
    lines.append("## 拦截成功详情")
    lines.append("")
    blocked = [r for r in results if r.get("blocked_by_arsguard")]
    for i, r in enumerate(blocked, 1):
        lines.append(f"- **{r.get('category_name', r.get('category', ''))}**: `{r['prompt'][:100]}...` (judge: {r.get('judge_verdict', 'N/A')})")
    lines.append("")

    lines.append("---")
    lines.append("*报告由 arsguard-eval 流水线自动生成*")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    path = os.path.join(os.path.dirname(__file__), "..", "data", "eval_results.json")
    if os.path.exists(path):
        with open(path) as f:
            results = json.load(f)
    else:
        results = []
    report = render_report(results)
    output = os.path.join(os.path.dirname(__file__), "..", "data", "report.md")
    with open(output, "w") as f:
        f.write(report)
    print(report)
