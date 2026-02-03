# 🎯 Stock Analysis Orchestrator

You coordinate the 3-agent stock analysis system. Run them in sequence, passing outputs between phases.

## Agents
1. **Researcher** — Scans market, generates watchlist
2. **Tracker** — Manages positions, decides buy/sell
3. **Analyst** — Reviews performance, updates learnings (weekly or when positions close)

## Daily Workflow

### Phase 1: Market Research
```
Spawn subagent with label "researcher-YYYY-MM-DD":
- Task: Follow agents/RESEARCHER.md workflow
- Model: opus
- Timeout: 30 minutes
- Wait for completion
```

**Handoff:** `watchlist/YYYY-MM-DD.json` created

### Phase 2: Position Tracking
```
Spawn subagent with label "tracker-YYYY-MM-DD":
- Task: Follow agents/TRACKER.md workflow
- Model: opus
- Timeout: 20 minutes
- Wait for completion
```

**Handoff:** `tracking/*.json` updated, `tracking/daily/YYYY-MM-DD.json` created

### Phase 3: Performance Analysis (Conditional)
Run Analyst if ANY of these conditions:
- Any position was closed today
- It's Friday (weekly review)
- >5 new closed positions since last analysis

```
Spawn subagent with label "analyst-YYYY-MM-DD":
- Task: Follow agents/ANALYST.md workflow
- Model: opus
- Timeout: 15 minutes
- Wait for completion
```

**Handoff:** `LEARNINGS.md` updated

## Execution

### Step 1: Spawn Researcher
```
sessions_spawn:
  task: |
    你是市场研究员。工作目录: /Users/bz/Work/Personal/stock-analysis
    
    严格按照 agents/RESEARCHER.md 执行:
    1. 读取 LEARNINGS.md
    2. 获取市场概览
    3. 扫描芝士财富全部股票 (~60只)
    4. 获取实时价格
    5. 深度研究候选股
    6. 输出 watchlist/YYYY-MM-DD.json 和 reports/YYYY-MM-DD.md
    7. Git commit
    
    完成后简要汇报: 扫描了X只股票，推荐X只，观望X只
  label: researcher-YYYY-MM-DD
  model: opus
  runTimeoutSeconds: 1800
```

### Step 2: Wait & Verify
Check that `watchlist/YYYY-MM-DD.json` exists before proceeding.

### Step 3: Spawn Tracker
```
sessions_spawn:
  task: |
    你是持仓管理员。工作目录: /Users/bz/Work/Personal/stock-analysis
    
    严格按照 agents/TRACKER.md 执行:
    1. 读取 LEARNINGS.md 和今日 watchlist
    2. 列出所有 tracking/*.json 持仓
    3. 获取实时价格
    4. 逐一评估: HOLD/SELL/RAISE_STOP
    5. 考虑是否开新仓位
    6. 输出 tracking/daily/YYYY-MM-DD.json
    7. Git commit
    
    完成后简要汇报: X只持仓，X只卖出，X只新开
  label: tracker-YYYY-MM-DD
  model: opus
  runTimeoutSeconds: 1200
```

### Step 4: Check if Analyst Needed
```bash
# Count closed positions today
CLOSED_TODAY=$(ls tracking/closed/*.json 2>/dev/null | wc -l)
DAY_OF_WEEK=$(date +%u)  # 5 = Friday

if [ $CLOSED_TODAY -gt 0 ] || [ $DAY_OF_WEEK -eq 5 ]; then
  # Run Analyst
fi
```

### Step 5: Spawn Analyst (if needed)
```
sessions_spawn:
  task: |
    你是绩效分析师。工作目录: /Users/bz/Work/Personal/stock-analysis
    
    严格按照 agents/ANALYST.md 执行:
    1. 分析 tracking/closed/ 中的已平仓位
    2. 识别胜负模式
    3. 计算统计数据
    4. 更新 LEARNINGS.md
    5. Git commit
    
    完成后简要汇报: 分析了X笔交易，胜率XX%，新增X条经验
  label: analyst-YYYY-MM-DD
  model: opus
  runTimeoutSeconds: 900
```

### Step 6: Final Summary
Send Telegram summary:
```
📊 A股分析系统 YYYY-MM-DD

🔬 研究: 扫描X只，推荐X只
📈 持仓: X只，+X只，-X只，平均盈亏X%
🧠 分析: [已运行/跳过]

详情: reports/YYYY-MM-DD.md
```

## File Structure
```
stock-analysis/
├── agents/
│   ├── RESEARCHER.md    # 市场研究员指南
│   ├── TRACKER.md       # 持仓管理员指南
│   ├── ANALYST.md       # 绩效分析师指南
│   └── ORCHESTRATOR.md  # 本文件
├── watchlist/
│   └── YYYY-MM-DD.json  # 每日研究输出
├── tracking/
│   ├── {code}.json      # 活跃持仓
│   ├── closed/          # 已平仓位
│   └── daily/           # 每日操作记录
├── reports/
│   └── YYYY-MM-DD.md    # 每日报告
├── scripts/
│   └── fetch_price.py   # 价格获取工具
├── LEARNINGS.md         # 累积经验
└── README.md
```

## Error Handling
- If Researcher fails: Skip Tracker, report error
- If Tracker fails: Still try Analyst if there are closed positions
- If Analyst fails: Log but don't block

## Model
All agents use `opus` (claude-opus-4-5) for best reasoning.
