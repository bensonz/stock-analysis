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

（空）

> 现在故意留空。全量扫描 158 次运行给出 13 条「需要改代码」，其中 5 条是
> `manifest-absent`、8 个日期是 `new-position-not-held`。两类都是**真缺陷**，
> 都在 `docs/HARNESS/TODO.md` 里有条目，所以它们应该继续喊——把它们塞进这个
> 文件只会让第一天就变成静音。
