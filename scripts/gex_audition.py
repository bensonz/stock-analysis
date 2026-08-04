#!/usr/bin/env python3
"""gex_audition.py — does the ETF-options GEX state deserve to graduate?

Read-only audition (three-tier doctrine, docs/backtest/RESULTS.md): measures
whether session-T gamma-exposure state has any next-session predictive content
before we let it touch the prompt or a rule.

Semantics (locked, see scripts/fetch_gex.py docstring, 2026-08-04 correction):
    regime = SIGN of total_net_gex directly
        > 0  净正gamma → dealer hedging DAMPENS moves
        < 0  净负gamma → dealer hedging AMPLIFIES moves
    flip_point = strike-profile zero-crossing (a structural landmark),
        NOT the SpotGamma "current regime boundary". Treated as its own
        dimension (spot-vs-flip distance), never used to re-derive regime.

Four questions (all point-in-time: state at T → outcome at/after T+1):
  Q1 Amplification — is next-session |return| larger after net-negative days?
  Q2 Direction    — any signed next-session return difference? (expected: no)
  Q3 Dist-to-flip — does spot-vs-flip add anything beyond net-GEX sign?
  Q4 Our book     — does GEX state predict the gate-pool 3-session stop-rate?
                    (reuses regime_detector.compute_stop_rate_series)

Returns are taken from the GEX history's OWN spot series (self-consistent).
Every number here is regenerable by re-running this script.

RIGOR: ~65-80 sessions x 5 underlyings that share the same market days are NOT
independent samples; net-negative GEX is a RARE state in this window. n per
bucket, mean±sd±se, and honest verdicts are printed for every test.

Usage:
    python3 scripts/gex_audition.py            # all tables
    python3 scripts/gex_audition.py --q1       # a single question
    GEX_BACKEND_URL=... python3 scripts/gex_audition.py
"""
import math
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

GEX_BACKEND_URL = (os.getenv("GEX_BACKEND_URL")
                   or "http://47.94.238.128:8080").rstrip("/")
HIST_API = f"{GEX_BACKEND_URL}/api/history/gex-history"

UNDERLYINGS = [
    ("510050", "50ETF"),
    ("510300", "300ETF"),
    ("510500", "500ETF"),
    ("588000", "科创50ETF"),
    ("159915", "创业板ETF"),
]

DAYS = 200


# ----------------------------------------------------------------------------
# data
# ----------------------------------------------------------------------------
def fetch_history(code: str) -> list[dict]:
    r = requests.get(HIST_API, params={"underlying": code, "days": DAYS},
                     timeout=30)
    r.raise_for_status()
    d = r.json()
    rows = d if isinstance(d, list) else d.get("data", [])
    rows = [x for x in rows if x.get("spot") and x.get("total_net_gex") is not None]
    rows.sort(key=lambda x: x["date"])
    return rows


def build_pairs(rows: list[dict]) -> list[dict]:
    """Each session T with a following session T+1: state at T, next return."""
    out = []
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        net = a["total_net_gex"]
        flip = a.get("flip_point")
        spot = a["spot"]
        ret = (b["spot"] / spot - 1.0) * 100.0
        out.append({
            "date": a["date"],
            "net": net,
            "sign": 1 if net > 0 else -1,
            "abs_net": abs(net),
            "dist_flip": ((spot / flip - 1.0) * 100.0) if flip else None,
            "ret": ret,
            "abs_ret": abs(ret),
        })
    return out


# ----------------------------------------------------------------------------
# stats helpers (no scipy dependency)
# ----------------------------------------------------------------------------
def _stats(xs: list[float]) -> tuple[int, float, float, float]:
    n = len(xs)
    if n == 0:
        return 0, float("nan"), float("nan"), float("nan")
    m = sum(xs) / n
    if n == 1:
        return 1, m, float("nan"), float("nan")
    sd = math.sqrt(sum((x - m) ** 2 for x in xs) / (n - 1))
    se = sd / math.sqrt(n)
    return n, m, sd, se


def _welch_t(a: list[float], b: list[float]) -> float:
    na, ma, sda, _ = _stats(a)
    nb, mb, sdb, _ = _stats(b)
    if na < 2 or nb < 2:
        return float("nan")
    se = math.sqrt(sda ** 2 / na + sdb ** 2 / nb)
    return (ma - mb) / se if se else float("nan")


def _pearson(xs, ys) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None
             and not math.isnan(x) and not math.isnan(y)]
    n = len(pairs)
    if n < 3:
        return float("nan")
    mx = sum(p[0] for p in pairs) / n
    my = sum(p[1] for p in pairs) / n
    num = sum((p[0] - mx) * (p[1] - my) for p in pairs)
    dx = math.sqrt(sum((p[0] - mx) ** 2 for p in pairs))
    dy = math.sqrt(sum((p[1] - my) ** 2 for p in pairs))
    return num / (dx * dy) if dx and dy else float("nan")


def _spearman(xs, ys) -> float:
    pairs = [(x, y) for x, y in zip(xs, ys)
             if x is not None and y is not None
             and not math.isnan(x) and not math.isnan(y)]
    if len(pairs) < 3:
        return float("nan")

    def ranks(vals):
        order = sorted(range(len(vals)), key=lambda i: vals[i])
        rk = [0.0] * len(vals)
        i = 0
        while i < len(vals):
            j = i
            while j + 1 < len(vals) and vals[order[j + 1]] == vals[order[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                rk[order[k]] = avg
            i = j + 1
        return rk
    rx = ranks([p[0] for p in pairs])
    ry = ranks([p[1] for p in pairs])
    return _pearson(rx, ry)


def _terciles(vals: list[float]) -> tuple[float, float]:
    s = sorted(vals)
    if len(s) < 3:
        return (float("nan"), float("nan"))
    return s[len(s) // 3], s[2 * len(s) // 3]


# ----------------------------------------------------------------------------
# Q1 / Q2 — amplification and direction
# ----------------------------------------------------------------------------
def q1_q2(all_pairs: dict[str, list[dict]]):
    print("=" * 74)
    print("Q1 放大效应 / Q2 方向 — 次日收益 vs 当日净GEX符号")
    print("  (次日收益取自GEX历史自身spot序列; 单位%)")
    print("=" * 74)
    pooled = [p for ps in all_pairs.values() for p in ps]

    print("\n[按标的] 净负gamma日计数 (稀有状态检查):")
    for code, name in UNDERLYINGS:
        ps = all_pairs.get(code, [])
        neg = sum(1 for p in ps if p["sign"] < 0)
        print(f"  {code} {name:<9} 配对n={len(ps):>3}  净负日={neg:>2}  净正日={len(ps)-neg:>3}")

    def bucket_report(pairs, tag):
        pos = [p["abs_ret"] for p in pairs if p["sign"] > 0]
        neg = [p["abs_ret"] for p in pairs if p["sign"] < 0]
        npos = _stats(pos); nneg = _stats(neg)
        print(f"\n[{tag}] 次日|收益| 按净GEX符号:")
        print(f"  {'桶':<14}{'n':>5}{'均值':>9}{'sd':>8}{'se':>8}")
        print(f"  {'净正gamma':<12}{npos[0]:>5}{npos[1]:>9.3f}{npos[2]:>8.3f}{npos[3]:>8.3f}")
        print(f"  {'净负gamma':<12}{nneg[0]:>5}{nneg[1]:>9.3f}{nneg[2]:>8.3f}{nneg[3]:>8.3f}")
        t = _welch_t(neg, pos)
        diff = (nneg[1] - npos[1]) if (nneg[0] and npos[0]) else float("nan")
        print(f"  差(负-正)={diff:+.3f}pp  Welchت={t:+.2f}"
              .replace("ت", "t"))
        # signed direction (Q2)
        spos = _stats([p["ret"] for p in pairs if p["sign"] > 0])
        sneg = _stats([p["ret"] for p in pairs if p["sign"] < 0])
        print(f"  [Q2 有符号次日收益] 净正 mean={spos[1]:+.3f} (n={spos[0]}) | "
              f"净负 mean={sneg[1]:+.3f} (n={sneg[0]})")

    bucket_report(pooled, "全体池合 (5标的; 注意非独立)")

    # magnitude terciles within sign — only meaningful where n allows
    print("\n[全体池合] 净正gamma日内, 按|净GEX|三分位的次日|收益|:")
    pos_pairs = [p for p in pooled if p["sign"] > 0]
    lo, hi = _terciles([p["abs_net"] for p in pos_pairs])
    b_lo = [p["abs_ret"] for p in pos_pairs if p["abs_net"] <= lo]
    b_mid = [p["abs_ret"] for p in pos_pairs if lo < p["abs_net"] <= hi]
    b_hi = [p["abs_ret"] for p in pos_pairs if p["abs_net"] > hi]
    for tag, b in [("低|净GEX|", b_lo), ("中", b_mid), ("高|净GEX|", b_hi)]:
        s = _stats(b)
        print(f"  {tag:<10} n={s[0]:>3} 均值={s[1]:.3f} sd={s[2]:.3f} se={s[3]:.3f}")
    print("  (净负gamma日样本过少, 不做三分位)")


# ----------------------------------------------------------------------------
# Q3 — distance to flip
# ----------------------------------------------------------------------------
def q3(all_pairs: dict[str, list[dict]]):
    print("\n" + "=" * 74)
    print("Q3 距flip — spot-vs-flip 是否在净GEX符号之外另有信息")
    print("=" * 74)
    pooled = [p for ps in all_pairs.values() for p in ps
              if p["dist_flip"] is not None]
    dist = [p["dist_flip"] for p in pooled]
    absret = [p["abs_ret"] for p in pooled]
    print(f"\n池合 n={len(pooled)}  dist_flip范围 [{min(dist):.2f}, {max(dist):.2f}]%")
    print(f"  corr(dist_flip, 次日|收益|):  Pearson={_pearson(dist, absret):+.3f} "
          f"Spearman={_spearman(dist, absret):+.3f}")
    print(f"  corr(|dist_flip|, 次日|收益|): "
          f"Pearson={_pearson([abs(d) for d in dist], absret):+.3f} "
          f"Spearman={_spearman([abs(d) for d in dist], absret):+.3f}")

    below = [p["abs_ret"] for p in pooled if p["dist_flip"] < 0]
    above = [p["abs_ret"] for p in pooled if p["dist_flip"] >= 0]
    sb, sa = _stats(below), _stats(above)
    print(f"\n  次日|收益| 按 spot vs flip:")
    print(f"    零轴下方(put-gamma区) n={sb[0]:>3} 均值={sb[1]:.3f} se={sb[3]:.3f}")
    print(f"    零轴上方(call-gamma区) n={sa[0]:>3} 均值={sa[1]:.3f} se={sa[3]:.3f}")
    # within positive-GEX only (the dominant regime): does dist add?
    pos = [p for p in pooled if p["sign"] > 0]
    print(f"\n  仅净正gamma日内 (主导状态, n={len(pos)}):")
    print(f"    corr(dist_flip, 次日|收益|): Pearson="
          f"{_pearson([p['dist_flip'] for p in pos], [p['abs_ret'] for p in pos]):+.3f}")


# ----------------------------------------------------------------------------
# Q4 — does GEX state predict our gate-pool stop-rate?
# ----------------------------------------------------------------------------
def q4(raw_by_code: dict[str, list[dict]]):
    print("\n" + "=" * 74)
    print("Q4 我们的池 — GEX状态 vs 门槛池3日止损率 (regime_detector复用)")
    print("=" * 74)
    import base_rates
    import regime_detector as rd
    panel = base_rates.get_panel(None)
    sr = rd.compute_stop_rate_series(panel)          # per-date forward-3d stop rate
    stop = {str(i)[:10]: float(v) for i, v in sr.items()}

    # daily GEX aggregates
    dates = sorted({r["date"] for rows in raw_by_code.values() for r in rows})
    net_neg_count = {}
    sign_300 = {}
    by_code_date = {c: {r["date"]: r for r in rows} for c, rows in raw_by_code.items()}
    for d in dates:
        cnt = 0; tot = 0
        for c in raw_by_code:
            r = by_code_date[c].get(d)
            if r:
                tot += 1
                if r["total_net_gex"] < 0:
                    cnt += 1
        net_neg_count[d] = cnt
        r3 = by_code_date.get("510300", {}).get(d)
        if r3:
            sign_300[d] = 1 if r3["total_net_gex"] > 0 else -1

    # align GEX[T] with stop_rate[T] (stop_rate[T] already measures T+1..T+3)
    common = [d for d in dates if d in stop]
    print(f"\n对齐窗口: {common[0]}..{common[-1]}  重叠交易日 n={len(common)}")
    print("  (stop_rate[T]=从T收盘起3日内跌破-5%的门槛池占比; 用GEX[T]预测之)")

    nnc = [net_neg_count[d] for d in common]
    st = [stop[d] for d in common]
    print(f"\n  corr(净负gamma标的数[0-5], stop_rate): "
          f"Pearson={_pearson(nnc, st):+.3f} Spearman={_spearman(nnc, st):+.3f}")

    zero = [stop[d] for d in common if net_neg_count[d] == 0]
    some = [stop[d] for d in common if net_neg_count[d] >= 1]
    sz, ss = _stats(zero), _stats(some)
    print(f"\n  stop_rate 按当日是否有净负gamma标的:")
    print(f"    0个净负   n={sz[0]:>3} 均值={sz[1]:.3f} sd={sz[2]:.3f} se={sz[3]:.3f}")
    print(f"    >=1个净负 n={ss[0]:>3} 均值={ss[1]:.3f} sd={ss[2]:.3f} se={ss[3]:.3f}")
    print(f"    差(有-无)={ss[1]-sz[1]:+.3f}  Welch t={_welch_t(some, zero):+.2f}")

    c300 = [d for d in common if d in sign_300]
    pos = [stop[d] for d in c300 if sign_300[d] > 0]
    neg = [stop[d] for d in c300 if sign_300[d] < 0]
    sp, sn = _stats(pos), _stats(neg)
    print(f"\n  stop_rate 按 510300(300ETF) 净GEX符号:")
    print(f"    300ETF净正 n={sp[0]:>3} 均值={sp[1]:.3f} se={sp[3]:.3f}")
    print(f"    300ETF净负 n={sn[0]:>3} 均值={sn[1]:.3f} se={sn[3]:.3f}")


# ----------------------------------------------------------------------------
def main():
    args = set(sys.argv[1:])
    print(f"GEX audition — backend {GEX_BACKEND_URL}\n")
    raw_by_code = {}
    for code, _ in UNDERLYINGS:
        try:
            raw_by_code[code] = fetch_history(code)
        except Exception as e:  # noqa: BLE001
            print(f"  ⚠️ {code} fetch failed: {e}")
            raw_by_code[code] = []
    all_pairs = {c: build_pairs(rows) for c, rows in raw_by_code.items()}

    run_all = not (args & {"--q1", "--q2", "--q3", "--q4"})
    if run_all or (args & {"--q1", "--q2"}):
        q1_q2(all_pairs)
    if run_all or "--q3" in args:
        q3(all_pairs)
    if run_all or "--q4" in args:
        q4(raw_by_code)


if __name__ == "__main__":
    main()
