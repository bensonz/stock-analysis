# 审计: 怎么用

每次运行后 20 分钟，`com.bz.stock-doctor` 会写一份判决到运行目录里：

```
runs/2026-08-21/afternoon/audit-result.md     ← 人看的
runs/2026-08-21/afternoon/audit-result.json   ← 机器读的（连续次数从这里推）
```

**每天一次，看当次运行：**

```bash
open runs/$(date +%F)/afternoon/audit-result.md
```

干净就是干净，没有别的意思。文件里会写清楚这次跑了几项检查、跳过了哪几项、
为什么跳过——静默放行才是要抓的谎。

**想知道"现在整个系统还有什么没修"，用这个：**

```bash
python3 scripts/doctor.py --open
```

它把所有运行的发现**按问题归并**，不按实例：一个 bug 在八天里犯了十一次，是
一件要去修的事，不是十一件。每组给出影响天数、最长连续次数、以及该改哪个文件。
退出码 1 表示有需要改代码的发现，可以直接挂进别的脚本。

其他用法：

```bash
python3 scripts/doctor.py                      # 审最近一次运行并打印
python3 scripts/doctor.py --date 2026-08-20 --slot noon
python3 scripts/doctor.py --since 2026-08-01   # 回填/重算一段时间
python3 scripts/doctor.py --open --since 2026-08-01   # 只看最近的未结项
```

---

# 已知并接受的审计发现

`scripts/doctor.py` 读这个文件，从不写它。这是整套审计里**唯一**由人手写的输入
——其余一切都从运行产物推导出来。

一条发现被列在这里，意思是"我们知道，而且现在不打算改"，不是"这不是问题"。
它仍然会出现在每天的 `audit-result.md` 里，仍然计连续次数，只是不再进
「需要改代码」区喊人。修好之后**删掉对应行**，不要打勾——留着的勾会变成又一个
说谎的状态信号，而这正是 Stage 1 要杀掉的东西。

格式，每行一条：

```
- <finding-id> — <为什么接受，以及在哪里跟踪>
```

`finding-id` 就是 `audit-result.json` 里的 `id` 字段，照抄即可。

## 当前接受的发现

- `new-position-not-held:002497` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-03-11 afternoon 的产物保持原样不改写
- `new-position-not-held:603191` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-03-11 afternoon 的产物保持原样不改写
- `new-position-not-held:600096` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-03-11 afternoon 的产物保持原样不改写
- `new-position-not-held:688025` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-04-08 afternoon 的产物保持原样不改写
- `new-position-not-held:688536` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-06-09 afternoon 的产物保持原样不改写
- `new-position-not-held:688652` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-06-09 afternoon 的产物保持原样不改写
- `new-position-not-held:002975` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-07-14 afternoon 的产物保持原样不改写
- `new-position-not-held:688536` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-07-31 afternoon 的产物保持原样不改写
- `new-position-not-held:000739` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-08-04 noon 的产物保持原样不改写
- `new-position-not-held:688019` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-08-17 noon 的产物保持原样不改写
- `new-position-not-held:688222` — 历史证据, 代码已于 2026-08-22 修复(run_daily.opened_new_positions); 2026-08-20 noon 的产物保持原样不改写

> 上面这些是 `newPositions` 写意图不写结果那个缺陷留下的历史实例。代码已修
> (2026-08-22, `run_daily.opened_new_positions`)，但那 8 天的 daily_summary.json
> 里确实写着假话——它们是证据，不改写。接受的是**具体实例 id**，不是检查本身，
> 所以换一只票再犯，照样会进「需要改代码」区喊人。
>
> `manifest-absent` 故意不接受: 它还没修，TODO Stage 4 里挂着，应该继续喊。
