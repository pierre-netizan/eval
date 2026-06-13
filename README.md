# arsguard-eval

安全测试框架，用于验证 [arsguard](https://github.com/anomalyco/opencode) 插件对 OWASP Top 10 for AI Agents 安全风险的拦截效果。

## 设计哲学

```
┌──────────┐    ┌──────────┐    ┌──────────┐    ┌─────────────┐
│  Gen     │ →  │  Eval    │ →  │  Report  │    │  Data 目录   │
│ 攻击生成  │    │ 拦截测试  │    │ 报告生成  │    │  gen/eval/  │
│          │    │          │    │ md/html  │    │  report/    │
│          │    │          │    │ tex/pdf  │    │  (隔离)      │
└──────────┘    └──────────┘    └──────────┘    └─────────────┘
```

- **三阶段流水线**: Gen (生成) → Eval (评估) → Report (报告)，每阶段可独立运行
- **Runner 插件架构**: 通过 `BaseRunner` 抽象基类 + `RunnerRegistry` 注册中心，可扩展任意攻击工具
- **数据驱动**: 所有攻击载荷以 JSON 格式存储，支持手工编辑和版本控制
- **多格式报告**: 同一组数据生成 Markdown / HTML / LaTeX / PDF 四种格式
- **多维度统计**: 按 OWASP 分类 + 工具子分类 + 具体钩子三层面分析拦截效果
- **每工具隔离**: 不同攻击工具 (hackmyagent / asb / promptfoo) 拥有独立数据目录
- **4-Cycle 测试**: 单工具测试 + 联合测试，验证不同攻击面下的拦截完整性
- **随机采样**: 从载荷池中均匀采样 N 条，避免测试集固定带来的偏差

## 目录结构

```
eval/
├── config/
│   └── eval.yaml                # 主配置
├── lib/
│   ├── base.py                  # BaseRunner 抽象基类
│   ├── tool_base.py             # ToolBaseRunner — dict 载荷格式支持
│   ├── registry.py              # RunnerRegistry 注册中心
│   ├── ollama.py                # Ollama API 客户端
│   ├── proxy.py                 # Squid 代理客户端
│   ├── judge.py                 # qwen3-0.6b 判定模块
│   └── reporter.py              # 报告数据统计工具
├── runners/
│   ├── hackmyagent_runner.py    # 100 条攻击, 每类有唯一子分类
│   ├── asb_runner.py            # 100 条攻击, DPI/OPI/MP/PoT 方法论
│   └── promptfoo_runner.py      # 100 条 promptfoo 风格载荷
├── scripts/
│   ├── test_cycle.py            # 4-Cycle 随机测试 (推荐入口)
│   ├── test_comprehensive.py    # 多工具测试 (--tool 筛选)
│   ├── run_all.sh               # 全流水线
│   ├── run_tool.sh <name>       # 单工具
│   ├── run_cycle.sh             # 4-Cycle
│   ├── run_watch.sh             # 文件变化自测
│   └── setup.sh                 # 环境检测 + 依赖安装
├── gen/                         # 攻击生成入口
├── eval/                        # 拦截测试入口
├── report/                      # 报告生成入口
├── data/                        # 输出 (gitignored)
│   ├── promptfoo/gen/
│   ├── promptfoo/eval/
│   ├── promptfoo/report/
│   ├── asb/gen/
│   ├── asb/eval/
│   ├── asb/report/
│   ├── hackmyagent/gen/
│   ├── hackmyagent/eval/
│   ├── hackmyagent/report/
│   ├── joint/gen/
│   ├── joint/eval/
│   └── joint/report/
└── README.md
```

## 快速开始

### 环境要求

| 工具 | 用途 | 可选 |
|------|------|------|
| Python 3.10+ | 运行框架 | 必选 |
| xelatex + ctex + Noto Serif CJK SC | PDF 报告 | 可选 |
| inotifywait (inotify-tools) | Watch 模式 | 可选 |

### 安装

```bash
# 安装 Python 依赖
pip install pyyaml jsonschema

# 检测环境
bash scripts/setup.sh
```

### 运行测试 (推荐)

```bash
# 4-Cycle 测试 (1000 条/轮, 全部 4 轮)
bash scripts/run_cycle.sh

# 单轮, 10 条快速验证
bash scripts/run_cycle.sh --n 10 --cycle hackmyagent

# 确定性种子
bash scripts/run_cycle.sh --n 100 --seed 42

# 全部参数
bash scripts/run_cycle.sh --n 500 --cycle asb --seed 123
```

### 全量测试 (arsguard 单元测试 + 4-Cycle)

```bash
# 顶层入口 (从仓库根目录)
bash run_tests.sh --quick
```

### 单工具测试

```bash
python3 scripts/test_comprehensive.py --tool hackmyagent
python3 scripts/test_comprehensive.py --tool asb
python3 scripts/test_comprehensive.py --tool promptfoo
```

### 分阶段运行

```bash
# 1. 只生成攻击载荷
python3 -c "from runners.hackmyagent_runner import HackMyAgentRunner; r = HackMyAgentRunner(); r.run_gen('data/hackmyagent/gen')"

# 2. 只执行评估
python3 -c "from runners.hackmyagent_runner import HackMyAgentRunner; r = HackMyAgentRunner(); r.run_eval('data/hackmyagent/gen/gen_attacks.json', 'data/hackmyagent/eval')"

# 3. 只生成报告
python3 -c "from runners.hackmyagent_runner import HackMyAgentRunner; r = HackMyAgentRunner(); r.run_report('data/hackmyagent/eval/eval_results.json', 'data/hackmyagent/report')"
```

### 自动重测 (Watch 模式)

```bash
# 检测文件变化后自动运行
bash scripts/run_watch.sh
```

## Runner 插件体系

### 概念

每个 Runner 是一个 Python 类，继承 `BaseRunner` 或 `ToolBaseRunner`，实现三个方法:

| 方法 | 用途 | 输入 | 输出 |
|------|------|------|------|
| `run_gen()` | 生成攻击载荷 | 输出目录 | `gen_attacks.json`, `gen_report.json` |
| `run_eval()` | 执行拦截测试 | 载荷 JSON | `eval_results.json`, `eval_report.json` |
| `run_report()` | 生成多格式报告 | 结果 JSON | `report.{md,html,tex,pdf}` |

### 载荷格式

支持字符串和字典两种格式:

```python
# 简洁格式 (字符串)
{"prompt": "Ignore previous instructions and ...", "category": "LLM01"}

# 详细格式 (带工具子分类)
{"prompt": "Ignore previous instructions and ...", "category": "LLM01",
 "tool": "hackmyagent",
 "tool_subcategory": "hackmyagent_direct",
 "tool_subcategory_name": "Direct Override"}
```

### 注册

```python
from lib.registry import RunnerRegistry
from runners.hackmyagent_runner import HackMyAgentRunner

RunnerRegistry.register("hackmyagent", HackMyAgentRunner)
```

## 攻击数据

| Runner | 载荷数 | 子分类体系 | 拦截率 |
|--------|--------|-----------|--------|
| hackmyagent | 100 | 每攻击唯一子分类 (Direct Override, Base64 Encoded, ...) | 100% |
| asb | 100 | 方法论子分类 (DPI, OPI, MP, PoT) | 100% |
| promptfoo | 100 | 场景子分类 (Output Handling, Model Theft, ...) | 37% |

## 报告格式

全部 4 种格式包含相同数据:

- **总体统计**: 总测试数, 拦截/绕过数, 拦截率
- **OWASP 分类统计**: 每分类的测试数/拦截数/拦截率
- **工具子分类统计**: 每子分类的测试数/拦截数/拦截率
- **拦截成功详情**: 每行显示 OWASP 分类 + 工具 + 子分类 + 拦截钩子 + 攻击提示
- **拦截失败详情**: 每行显示 OWASP 分类 + 工具 + 子分类 + Judge 判定 + 攻击提示

### 报告列说明

| 列 | 含义 | 示例 |
|----|------|------|
| OWASP 分类 | LLM01-LLM10 | LLM01: Prompt Injection |
| 工具 | 攻击源 | hackmyagent, asb, promptfoo |
| 子分类 | 工具内子类别 | Direct Override, DPI - System Override |
| 拦截钩子 | 实际拦截的钩子 | llm01_prompt_injection |
| Judge 判定 | 模型二次判定 | blocked, bypassed |

## 测试周期

4-Cycle 测试模式:

| Cycle | 工具 | 目的 |
|-------|------|------|
| 1. promptfoo-only | promptfoo | 验证场景化攻击 |
| 2. asb-only | asb | 验证方法论攻击 |
| 3. hackmyagent-only | hackmyagent | 验证多样化攻击 |
| 4. joint | 全部工具混合 | 验证综合场景 |

每条攻击日志格式:
```
[序号/总数] <工具>/<子分类>: [BLOCK|BYPASS] <钩子名>: <匹配原因>
```

## 配置

`config/eval.yaml`:

```yaml
judge:
  model: "qwen3-0.6b"
  url: "http://localhost:11434/api/generate"

runner:
  default: "direct"
  promptfoo:
    binary: "promptfoo"
```

## 关键钩子

所有 10 个 OWASP 钩子位于 `arsguard/src/plugins/hooks/llm{01..10}_*.py`:

| 编号 | 名称 | 检测策略 |
|------|------|---------|
| LLM01 | Prompt Injection | 30+ 注入模式 + 系统提示覆盖 |
| LLM02 | Insecure Output | 20+ XSS/数据泄露模式 |
| LLM03 | Training Data Poisoning | 30+ 投毒模式 |
| LLM04 | Model DoS | 15+ DoS 模式 + 速率限制 |
| LLM05 | Supply Chain | 25+ 供应链攻击模式 |
| LLM06 | Sensitive Info | 20+ 正则 (邮箱/电话/密钥等) |
| LLM07 | Insecure Plugin | 20+ 危险函数 + 不安全来源 |
| LLM08 | Excessive Agency | 25+ 命令模式 + 结构化检查 |
| LLM09 | Overreliance | 25+ 置信度覆盖 + 确定性断言 |
| LLM10 | Model Theft | 30+ 提取指示器 + 会话累计 |

## 常见问题

**Q**: PDF 报告乱码?
**A**: 需要 Noto Serif CJK SC 字体: `apt install fonts-noto-cjk`。检查 `xelatex -v`。

**Q**: 拦截率低怎么办?
**A**: 修改 `arsguard/src/plugins/hooks/` 中对应钩子的模式列表，然后重新运行测试。

**Q**: 如何添加新的攻击工具?
**A**: 创建 `runners/your_tool_runner.py`，继承 `ToolBaseRunner`，实现三个方法，调用 `RunnerRegistry.register("name", YourRunner)` 注册。
