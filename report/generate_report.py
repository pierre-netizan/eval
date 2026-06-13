"""Report generator — renders Markdown / HTML / LaTeX test reports from eval results.

Supports per-tool and combined (n+1) report output with tool_label parameter.

Functions:
    render_markdown: Generate a Markdown-formatted report.
    render_html: Generate a standalone HTML report with embedded CSS.
    render_latex: Generate a LaTeX document for PDF compilation via xelatex.
    save_reports: Write all three formats to disk (optionally compile PDF).
    save_all_reports: Write per-tool reports plus a combined "all" report.
"""

import json
import os
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.reporter import calc_stats


def _tool_header(tool_label: str = "") -> str:
    """Return a suffix string for the report title when a specific tool is named.

    Args:
        tool_label: Optional tool name (e.g. "direct", "promptfoo").

    Returns:
        " - <tool_label>" if tool_label is non-empty, otherwise "".
    """
    if tool_label:
        return f" - {tool_label}"
    return ""


def render_markdown(results: list, tool_label: str = "") -> str:
    """Render test results as a Markdown report.

    The report includes: overall stats summary table, per-OWASP-category
    breakdown, per-tool-subcategory breakdown, bypassed (failed interception)
    detail table, and successful interception detail table.

    Args:
        results: List of result dicts, each containing keys like
            "category", "blocked_by_arsguard", "blocking_hook", "prompt", etc.
        tool_label: Optional tool name shown in the report title.

    Returns:
        A Markdown-formatted string.
    """
    stats = calc_stats(results)
    lines = []
    lines.append(f"# arsguard 安全测试报告{_tool_header(tool_label)}")
    lines.append("")
    lines.append(f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    if tool_label:
        lines.append(f"**测试工具**: {tool_label}")
    lines.append("")
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
    lines.append("## 按 OWASP 分类统计")
    lines.append("")
    lines.append("| OWASP 分类 | 测试数 | 拦截数 | 拦截率 | Judge 一致率 |")
    lines.append("|------------|--------|--------|--------|-------------|")
    for cat, s in stats.get("by_category", {}).items():
        lines.append(f"| {s['name']} | {s['total']} | {s['blocked']} | {s['block_rate']:.0f}% | {s['consensus_rate']:.0f}% |")
    lines.append("")
    lines.append("## 按工具子分类统计")
    lines.append("")
    lines.append("| 工具 | 子分类 | 测试数 | 拦截数 | 拦截率 |")
    lines.append("|------|--------|--------|--------|--------|")
    for key, s in stats.get("by_subcategory", {}).items():
        lines.append(f"| {s['tool']} | {s['subcategory_name']} | {s['total']} | {s['blocked']} | {s['block_rate']:.0f}% |")
    lines.append("")
    lines.append("## 拦截失败详情 (Bypassed)")
    lines.append("")
    bypassed = [r for r in results if not r.get("blocked_by_arsguard")]
    if bypassed:
        lines.append("| # | OWASP 分类 | 测试工具 | 工具子分类 | 攻击提示 |")
        lines.append("|---|------------|----------|------------|----------|")
        for i, r in enumerate(bypassed, 1):
            tool = r.get("tool", "?")
            subcat = r.get("tool_subcategory_name", "")
            tag = f" ({tool}/{subcat})" if subcat else f" ({tool})"
            lines.append(f"| {i} | {r.get('category_name', r.get('category', 'unknown'))}{tag} | {tool} | {subcat} | `{r['prompt'][:120]}` |")
        lines.append("")
    else:
        lines.append("**全部拦截成功！未发现绕过。**")
        lines.append("")
    lines.append("## 拦截成功详情")
    lines.append("")
    lines.append("| # | OWASP 分类 | 测试工具 | 工具子分类 | 拦截钩子 | 攻击提示 |")
    lines.append("|---|------------|----------|------------|----------|----------|")
    blocked = [r for r in results if r.get("blocked_by_arsguard")]
    for i, r in enumerate(blocked, 1):
        tool = r.get("tool", "?")
        subcat = r.get("tool_subcategory_name", "")
        hook = r.get("blocking_hook", r.get("judge_verdict", "?"))
        lines.append(f"| {i} | {r.get('category_name', r.get('category', ''))} | {tool} | {subcat} | {hook} | `{r['prompt'][:100]}...` |")
    lines.append("")
    lines.append("---")
    lines.append("*报告由 arsguard-eval 流水线自动生成*")
    lines.append("")
    return "\n".join(lines)


def render_html(results: list, tool_label: str = "") -> str:
    """Render test results as a standalone HTML report with embedded CSS styling.

    Includes summary cards (total, blocked, bypassed, block rate), per-category
    and per-subcategory tables, and detail tables for bypassed/blocked results.
    Blocked rows are green-tinted, bypassed rows are red-tinted.

    Args:
        results: List of result dicts (same structure as render_markdown).
        tool_label: Optional tool name shown in the report title.

    Returns:
        A complete HTML document string.
    """
    stats = calc_stats(results)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    th = _tool_header(tool_label)

    cat_rows = ""
    for cat, s in stats.get("by_category", {}).items():
        rate_color = "green" if s["block_rate"] >= 80 else "orange" if s["block_rate"] >= 50 else "red"
        cat_rows += f"""<tr>
            <td>{s['name']}</td>
            <td>{s['total']}</td>
            <td>{s['blocked']}</td>
            <td><span class="rate-{rate_color}">{s['block_rate']:.0f}%</span></td>
            <td>{s['consensus_rate']:.0f}%</td>
        </tr>\n"""

    subcat_rows = ""
    for key, s in stats.get("by_subcategory", {}).items():
        rate_color = "green" if s["block_rate"] >= 80 else "orange" if s["block_rate"] >= 50 else "red"
        subcat_rows += f"""<tr>
            <td>{s['tool']}</td>
            <td>{s['subcategory_name']}</td>
            <td>{s['total']}</td>
            <td>{s['blocked']}</td>
            <td><span class="rate-{rate_color}">{s['block_rate']:.0f}%</span></td>
        </tr>\n"""

    bypassed_rows = ""
    for i, r in enumerate(
        (r for r in results if not r.get("blocked_by_arsguard")), 1
    ):
        tool = r.get("tool", "?")
        subcat = r.get("tool_subcategory_name", "")
        bypassed_rows += f"""<tr class="bypassed">
            <td>{i}</td>
            <td>{r.get('category_name', r.get('category', ''))}</td>
            <td>{tool}</td>
            <td>{subcat}</td>
            <td><code>{r['prompt'][:200]}</code></td>
            <td>{r.get('judge_verdict', 'N/A')}</td>
        </tr>\n"""

    blocked_rows = ""
    for i, r in enumerate(
        (r for r in results if r.get("blocked_by_arsguard")), 1
    ):
        tool = r.get("tool", "?")
        subcat = r.get("tool_subcategory_name", "")
        hook = r.get("blocking_hook", r.get("judge_verdict", "?"))
        blocked_rows += f"""<tr class="blocked">
            <td>{i}</td>
            <td>{r.get('category_name', r.get('category', ''))}</td>
            <td>{tool}</td>
            <td>{subcat}</td>
            <td>{hook}</td>
            <td><code>{r['prompt'][:200]}</code></td>
        </tr>\n"""

    tool_info = f"<p><strong>测试工具</strong>: {tool_label}</p>\n" if tool_label else ""

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>arsguard 安全测试报告{th}</title>
<style>
body {{ font-family: -apple-system, 'Noto Sans CJK SC', 'Segoe UI', sans-serif; max-width: 960px; margin: 2em auto; padding: 0 1em; color: #333; background: #fafafa; }}
h1 {{ color: #1a1a2e; border-bottom: 3px solid #e94560; padding-bottom: .3em; }}
h2 {{ color: #16213e; margin-top: 1.5em; }}
table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #16213e; color: #fff; }}
tr:nth-child(even) {{ background: #f5f5f5; }}
td.rate-green {{ color: #2ecc71; font-weight: bold; }}
td.rate-orange {{ color: #f39c12; font-weight: bold; }}
td.rate-red {{ color: #e74c3c; font-weight: bold; }}
code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; font-size: .9em; word-break: break-all; }}
.blocked td {{ background: #e8f5e9; }}
.bypassed td {{ background: #ffebee; }}
.summary {{ display: flex; gap: 1.5em; flex-wrap: wrap; margin: 1em 0; }}
.summary-card {{ flex: 1; min-width: 140px; background: #fff; border-radius: 8px; padding: 1em; text-align: center; box-shadow: 0 2px 4px rgba(0,0,0,.1); }}
.summary-card .num {{ font-size: 2em; font-weight: bold; }}
.summary-card .label {{ font-size: .85em; color: #666; margin-top: .3em; }}
.summary-card.green .num {{ color: #2ecc71; }}
.summary-card.red .num {{ color: #e74c3c; }}
.summary-card.blue .num {{ color: #3498db; }}
.summary-card.orange .num {{ color: #f39c12; }}
.footer {{ margin-top: 2em; color: #999; font-size: .85em; text-align: center; }}
</style>
</head>
<body>
<h1>arsguard 安全测试报告{th}</h1>
<p><strong>生成时间</strong>: {now}</p>
{tool_info}

<h2>总体统计</h2>
<div class="summary">
    <div class="summary-card blue"><div class="num">{stats['total']}</div><div class="label">总测试数</div></div>
    <div class="summary-card green"><div class="num">{stats['blocked']}</div><div class="label">拦截成功</div></div>
    <div class="summary-card red"><div class="num">{stats['bypassed']}</div><div class="label">拦截失败</div></div>
    <div class="summary-card orange"><div class="num">{stats['block_rate']:.1f}%</div><div class="label">拦截率</div></div>
</div>

<h2>按 OWASP 分类统计</h2>
<table>
<tr><th>分类</th><th>测试数</th><th>拦截数</th><th>拦截率</th><th>Judge 一致率</th></tr>
{cat_rows}
</table>

<h2>按工具子分类统计</h2>
<table>
<tr><th>工具</th><th>子分类</th><th>测试数</th><th>拦截数</th><th>拦截率</th></tr>
{subcat_rows}
</table>

<h2>拦截失败详情 (Bypassed)</h2>
<table>
<tr><th>#</th><th>OWASP 分类</th><th>工具</th><th>子分类</th><th>攻击提示</th><th>Judge 判定</th></tr>
{bypassed_rows if bypassed_rows else '<tr><td colspan="6" style="text-align:center;color:#2ecc71;">全部拦截成功！未发现绕过。</td></tr>'}
</table>

<h2>拦截成功详情</h2>
<table>
<tr><th>#</th><th>OWASP 分类</th><th>工具</th><th>子分类</th><th>拦截钩子</th><th>攻击提示</th></tr>
{blocked_rows if blocked_rows else '<tr><td colspan="6" style="text-align:center;">无拦截记录。</td></tr>'}
</table>

<div class="footer">报告由 arsguard-eval 流水线自动生成</div>
</body>
</html>"""


def render_latex(results: list, tool_label: str = "") -> str:
    """Render test results as a LaTeX document suitable for PDF compilation via xelatex.

    Uses the ctex package for CJK support, longtable for multi-page detail
    tables, and xcolor for color-coded block rates (green/orange/red).

    Args:
        results: List of result dicts (same structure as render_markdown).
        tool_label: Optional tool name shown in the title.

    Returns:
        A complete LaTeX document string.
    """
    stats = calc_stats(results)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    th = _tool_header(tool_label)
    title_extra = f" \\\\ {tool_label}" if tool_label else ""

    rows = ""
    for cat, s in stats.get("by_category", {}).items():
        esc = s["name"].replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")
        rate = s["block_rate"]
        color = "green!60" if rate >= 80 else "orange!80" if rate >= 50 else "red!80"
        rows += f"            {esc} & {s['total']} & {s['blocked']} & "
        rows += f"\\textcolor{{{color}}}{{{rate:.0f}\\%}} & {s['consensus_rate']:.0f}\\% \\\\\n"

    subcat_rows = ""
    for key, s in stats.get("by_subcategory", {}).items():
        esc_tool = s["tool"].replace("&", "\\&").replace("_", "\\_")
        esc_name = s["subcategory_name"].replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")
        rate = s["block_rate"]
        color = "green!60" if rate >= 80 else "orange!80" if rate >= 50 else "red!80"
        subcat_rows += f"            {esc_tool} & {esc_name} & {s['total']} & {s['blocked']} & "
        subcat_rows += f"\\textcolor{{{color}}}{{{rate:.0f}\\%}} \\\\\n"

    def esc_tex(s, maxlen=80):
        """Escape special LaTeX characters and truncate a string.

        Replaces characters that have special meaning in LaTeX
        (\, &, %, _, #, {, }, ~, ^) with their escaped equivalents.
        Also removes newlines and truncates to maxlen characters.

        Args:
            s: The raw input string.
            maxlen: Maximum character length before truncation (default 80).

        Returns:
            A LaTeX-safe, truncated string.
        """
        text = s[:maxlen]
        text = text.replace("\n", " ").replace("\r", "")
        text = text.replace("\\", "\\textbackslash{}")
        text = text.replace("&", "\\&").replace("%", "\\%")
        text = text.replace("_", "\\_").replace("#", "\\#")
        text = text.replace("{", "\\{").replace("}", "\\}")
        text = text.replace("~", "\\textasciitilde{}")
        text = text.replace("^", "\\textasciicircum{}")
        return text

    bypassed_rows = ""
    for i, r in enumerate(
        (r for r in results if not r.get("blocked_by_arsguard")), 1
    ):
        esc_name = esc_tex(r.get("category_name", r.get("category", "")), 30)
        esc_tool = esc_tex(r.get("tool", "?"), 12)
        esc_subcat = esc_tex(r.get("tool_subcategory_name", ""), 20)
        esc_prompt = esc_tex(r["prompt"], 60)
        bypassed_rows += (
            f"            {i} & {esc_name} & {esc_tool} & {esc_subcat} & "
            f"{r.get('judge_verdict', 'N/A')} & "
            f"{esc_prompt} \\\\\n"
        )

    blocked_rows = ""
    for i, r in enumerate(
        (r for r in results if r.get("blocked_by_arsguard")), 1
    ):
        esc_name = esc_tex(r.get("category_name", r.get("category", "")), 30)
        esc_tool = esc_tex(r.get("tool", "?"), 12)
        esc_subcat = esc_tex(r.get("tool_subcategory_name", ""), 20)
        esc_hook = esc_tex(r.get("blocking_hook", r.get("judge_verdict", "?")), 20)
        esc_prompt = esc_tex(r["prompt"], 60)
        blocked_rows += (
            f"            {i} & {esc_name} & {esc_tool} & {esc_subcat} & "
            f"{esc_hook} & "
            f"{esc_prompt} \\\\\n"
        )

    col_c_def = r'\newcolumntype{C}{>{\centering\arraybackslash}p{0.6cm}}'
    col_m_def = r'\newcolumntype{M}{>{\raggedright\arraybackslash}p{2.5cm}}'
    col_k_def = r'\newcolumntype{K}{>{\raggedright\arraybackslash}p{1.2cm}}'
    col_s_def = r'\newcolumntype{S}{>{\raggedright\arraybackslash}p{2cm}}'
    col_j_def = r'\newcolumntype{J}{>{\raggedright\arraybackslash}p{2cm}}'
    col_l_def = r'\newcolumntype{L}{>{\raggedright\arraybackslash}p{5cm}}'
    noc = '            \\multicolumn{{4}}{{c}}'
    fallback_none = noc + '{{无拦截记录。}} \\\\'
    fallback_all_ok = noc + '{{全部拦截成功！未发现绕过。}} \\\\'
    return rf"""\documentclass[12pt,a4paper]{{article}}

\usepackage[UTF8]{{ctex}}
\usepackage{{fontspec}}
\usepackage{{xcolor}}
\usepackage{{booktabs}}
\usepackage{{longtable}}
\usepackage{{tabularx}}
\usepackage{{geometry}}
\usepackage{{hyperref}}
\usepackage{{titlesec}}
\usepackage{{array}}

\geometry{{margin=2cm}}

\setmainfont{{Noto Serif CJK SC}}
\setCJKmainfont{{Noto Serif CJK SC}}
\setCJKsansfont{{Noto Sans CJK SC}}
\setCJKmonofont{{AR PL UMing TW MBE}}

\definecolor{{green}}{{RGB}}{{46,204,113}}
\definecolor{{red}}{{RGB}}{{231,76,60}}
\definecolor{{orange}}{{RGB}}{{243,156,18}}
\definecolor{{blue}}{{RGB}}{{52,152,219}}

{col_c_def}
{col_m_def}
{col_k_def}
{col_s_def}
{col_j_def}
{col_l_def}

\title{{arsguard 安全测试报告{title_extra}}}
\date{{{now}}}

\begin{{document}}

\maketitle
\thispagestyle{{empty}}

\section*{{总体统计}}

\begin{{center}}
\begin{{tabular}}{{cccc}}
\toprule
\textbf{{总测试数}} & \textbf{{拦截成功}} & \textbf{{拦截失败}} & \textbf{{拦截率}} \\
\midrule
{stats['total']} & {stats['blocked']} & {stats['bypassed']} & {stats['block_rate']:.1f}\% \\
\bottomrule
\end{{tabular}}
\end{{center}}

\vspace{{1em}}

\begin{{center}}
\begin{{tabular}}{{cc}}
\toprule
\textbf{{Judge 判定拦截}} & \textbf{{Judge 一致率}} \\
\midrule
{stats['judged_blocked']} & {stats['judge_consensus_rate']:.1f}\% \\
\bottomrule
\end{{tabular}}
\end{{center}}

\section*{{按 OWASP 分类统计}}

\begin{{center}}
\begin{{tabular}}{{lcccc}}
\toprule
\textbf{{分类}} & \textbf{{测试数}} & \textbf{{拦截数}} & \textbf{{拦截率}} & \textbf{{一致率}} \\
\midrule
{rows}\bottomrule
\end{{tabular}}
\end{{center}}

\section*{{按工具子分类统计}}

\begin{{center}}
\begin{{tabular}}{{llccc}}
\toprule
\textbf{{工具}} & \textbf{{子分类}} & \textbf{{测试数}} & \textbf{{拦截数}} & \textbf{{拦截率}} \\
\midrule
{subcat_rows}\bottomrule
\end{{tabular}}
\end{{center}}

\newpage
\section*{{拦截成功详情}}

\begin{{longtable}}{{CMKSJL}}
\toprule
\textbf{{\#}} & \textbf{{OWASP}} & \textbf{{工具}} & \textbf{{子分类}} & \textbf{{钩子}} & \textbf{{攻击提示}} \\
\midrule
\endhead
{blocked_rows if blocked_rows else fallback_none}
\bottomrule
\end{{longtable}}

\newpage
\section*{{拦截失败详情 (Bypassed)}}

\begin{{longtable}}{{CMKSJL}}
\toprule
\textbf{{\#}} & \textbf{{OWASP}} & \textbf{{工具}} & \textbf{{子分类}} & \textbf{{Judge}} & \textbf{{攻击提示}} \\
\midrule
\endhead
{bypassed_rows if bypassed_rows else fallback_all_ok}
\bottomrule
\end{{longtable}}

\vfill
\begin{{center}}
\textcolor{{gray}}{{\footnotesize 报告由 arsguard-eval 流水线自动生成}}
\end{{center}}

\end{{document}}"""


def render_report(results: list, tool_label: str = "") -> str:
    """Generate markdown report (backward-compatible convenience wrapper).

    Args:
        results: List of result dicts.
        tool_label: Optional tool name for the report title.

    Returns:
        Markdown-formatted report string.
    """
    return render_markdown(results, tool_label=tool_label)


def save_reports(results: list, output_dir: str = "data", compile_pdf: bool = True,
                 filename_prefix: str = "report", tool_label: str = "") -> dict:
    """Save all report formats (Markdown, HTML, LaTeX, optional PDF) to disk.

    Creates the output directory if it does not exist. Writes three report
    files (<prefix>.md, <prefix>.html, <prefix>.tex). If compile_pdf is True
    and xelatex is available, compiles the LaTeX source to a PDF. Temporary
    LaTeX build artifacts (.aux, .log, .out) are cleaned up. The xelatex
    log is saved to <prefix>_xelatex.log on failure.

    Args:
        results: List of result dicts.
        output_dir: Target directory for report files (default "data").
        compile_pdf: If True, attempt PDF compilation via xelatex (default True).
        filename_prefix: Base filename without extension (default "report").
        tool_label: Optional tool name for the report title.

    Returns:
        Dict with format keys ("md", "html", "tex", optionally "pdf") mapped
        to file paths. If PDF compilation fails, "pdf_error" contains the log path.
    """
    os.makedirs(output_dir, exist_ok=True)
    md = render_markdown(results, tool_label=tool_label)
    html = render_html(results, tool_label=tool_label)
    tex = render_latex(results, tool_label=tool_label)

    paths = {}

    md_path = os.path.join(output_dir, f"{filename_prefix}.md")
    with open(md_path, "w") as f:
        f.write(md)
    paths["md"] = md_path

    html_path = os.path.join(output_dir, f"{filename_prefix}.html")
    with open(html_path, "w") as f:
        f.write(html)
    paths["html"] = html_path

    tex_path = os.path.join(output_dir, f"{filename_prefix}.tex")
    with open(tex_path, "w") as f:
        f.write(tex)
    paths["tex"] = tex_path

    if compile_pdf:
        pdf_path = os.path.join(output_dir, f"{filename_prefix}.pdf")
        try:
            result = subprocess.run(
                ["xelatex", "-interaction=nonstopmode", "-output-directory", output_dir, tex_path],
                capture_output=True, text=True, timeout=120,
            )
            # Save xelatex log regardless of success/failure for debugging
            log_path = os.path.join(output_dir, f"{filename_prefix}_xelatex.log")
            with open(log_path, "w") as f:
                f.write(result.stdout + "\n--- STDERR ---\n" + result.stderr)
            if result.returncode == 0:
                paths["pdf"] = pdf_path
            else:
                print(f"[report] xelatex returned {result.returncode}, see {log_path}", file=sys.stderr)
                paths["pdf_error"] = log_path
            # Clean up temporary LaTeX build artifacts
            for aux in (f"{filename_prefix}.aux", f"{filename_prefix}.log", f"{filename_prefix}.out"):
                p = os.path.join(output_dir, aux)
                if os.path.exists(p):
                    os.remove(p)
        except FileNotFoundError:
            print("[report] xelatex not found, skipping PDF", file=sys.stderr)
        except Exception as e:
            print(f"[report] PDF compilation failed: {e}", file=sys.stderr)

    return paths


def save_all_reports(results_by_tool: dict, combined_results: list,
                     output_dir: str = "data", compile_pdf: bool = True) -> dict:
    """Save per-tool reports plus a combined (n+1) report.

    Each tool in results_by_tool gets its own report with filename_prefix
    "report_<tool_name>". A final "report_all" is generated from the merged
    combined_results under the key "all".

    Args:
        results_by_tool: Dict mapping tool names (str) to their result lists.
        combined_results: Merged results list from all tools.
        output_dir: Target directory for all report files (default "data").
        compile_pdf: If True, attempt PDF compilation for each report.

    Returns:
        Dict of {tool_name: {format: path}}, including the "all" key.
    """
    all_paths = {}
    for tool_name, results in results_by_tool.items():
        paths = save_reports(results, output_dir=output_dir, compile_pdf=compile_pdf,
                             filename_prefix=f"report_{tool_name}",
                             tool_label=tool_name)
        all_paths[tool_name] = paths
    # Combined report
    combined_paths = save_reports(combined_results, output_dir=output_dir, compile_pdf=compile_pdf,
                                  filename_prefix="report_all",
                                  tool_label="all")
    all_paths["all"] = combined_paths
    return all_paths


if __name__ == "__main__":
    """CLI entry point: load eval results from a JSON file and generate reports.

    Usage:
        python generate_report.py --results path/to/eval_results.json --prefix my_report --tool direct

    Arguments:
        --results: Path to eval results JSON (default: ../data/eval_results.json).
        --prefix:  Report filename prefix (default: "report").
        --tool:    Optional tool label for the report title (default: "").
        --no-pdf:  Skip PDF compilation (default: False, i.e. compile PDF).
    """
    import argparse
    parser = argparse.ArgumentParser(description="Generate arsguard test reports from eval results.")
    parser.add_argument("--results", default=os.path.join(os.path.dirname(__file__), "..", "data", "eval_results.json"))
    parser.add_argument("--prefix", default="report")
    parser.add_argument("--tool", default="")
    parser.add_argument("--no-pdf", action="store_true")
    args = parser.parse_args()

    path = args.results
    if os.path.exists(path):
        with open(path) as f:
            results = json.load(f)
    else:
        results = []
    paths = save_reports(results, filename_prefix=args.prefix,
                         tool_label=args.tool, compile_pdf=not args.no_pdf)
    for fmt, p in paths.items():
        print(f"  [{fmt}] {p}")
