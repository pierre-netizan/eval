# eval project — arsguard 安全测试框架
# 三阶段流水线：Gen → Eval → Report
# 支持多种 test runner 扩展

## 项目结构
```
eval/
├── check_tag.sh                # 一键稳定性检查 + 版本提交
├── lib/                        # 共享库
│   ├── base.py                 # BaseRunner 抽象基类
│   ├── registry.py             # RunnerRegistry 注册中心
│   ├── ollama.py               # Ollama API 客户端
│   ├── proxy.py                # Squid 代理客户端
│   ├── judge.py                # qwen3-0.6b 判定模块
│   └── reporter.py             # 报告工具
├── runners/                    # Runner 扩展目录
│   ├── direct_runner.py        # 直接 Python runner（默认）
│   └── promptfoo_runner.py     # promptfoo CLI runner
├── gen/                        # 攻击生成（供 direct_runner 使用）
├── eval/                       # 拦截测试（供 direct_runner/arsguard_provider）
├── report/                     # 报告生成（供 direct_runner）
├── config/promptfoo/           # promptfoo 配置文件
├── scripts/                    # 运行脚本
├── docker/                     # 测试环境 Docker 编排
└── data/                       # 输出数据（gitignored）
```

## 分支策略
| 分支 | 用途 | Squid 规则 |
|------|------|-----------|
| `main` | 通用基础 | 全量配置 |
| `ws` | WebSocket 通信 | 支持 CONNECT/WebSocket 升级 |
| `http` | HTTP-only | 禁止 WebSocket，限制 CONNECT |

## 运行命令
```bash
# 一键版本提交（默认 5 轮，≤5% 则自动提交子仓库 → 父仓库 → tag）
./check_tag.sh
./check_tag.sh --threshold 3
./check_tag.sh --rounds 3 --n 500

# 手动测试
bash scripts/run_round.sh                    # 1 轮
bash scripts/run_round.sh --rounds 5         # 5 轮

# 结果分析
python3 scripts/round_analyzer.py --round 1
python3 scripts/round_analyzer.py --round 1 --fp

# 定时任务
bash scripts/setup_cron.sh --daily
bash scripts/setup_cron.sh --status

# 全流程（旧接口）
bash scripts/run_all.sh

# 设置测试环境
bash scripts/setup.sh
```

## 技术栈
- Python 3.10+
- Ollama（qwen3-0.6b 目标模型 + Qwen3-4B-Instruct 提示生成）
- promptfoo（可选，作为 runner 之一）
- Docker Compose（测试环境）
