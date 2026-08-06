#!/usr/bin/env python3
"""Static portfolio-overview site generator → site/index.html.

Single self-contained HTML file: inline data + inline SVG/JS chart, zero
CDN/network dependencies (must render offline). Color convention is
A-share: red = gain, green = loss.

Data sources (数字纪律 — everything re-derivable):
  - runs/<date>[/<slot>]/input/positions_snapshot.json → daily equity curve
    (per date the LATEST snapshot wins, ordered by snapshot_time; legacy
    no-slot layout supported)
  - tracking/positions.json → current portfolio + active positions
  - tracking/closed/*.json  → trade history + win-rate stats

Regenerate: python3 scripts/build_site.py
Also runs automatically at the end of run_daily.py (non-fatal, pre-commit).
"""

import html
import json
import re
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
RUNS_DIR = PROJECT_ROOT / "runs"
TRACKING_DIR = PROJECT_ROOT / "tracking"
SITE_DIR = PROJECT_ROOT / "site"

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _snapshot_point(path: Path):
    """Extract one equity point from a positions_snapshot.json, or None."""
    try:
        snap = _read_json(path)
        pf = (snap.get("positions_json") or {}).get("portfolio") or {}
        if not pf.get("startingCapital"):
            return None
        return {
            "time": snap.get("snapshot_time", ""),
            "equity": pf.get("totalEquity"),
            "cash": pf.get("cash"),
            "invested": pf.get("investedValue"),
            "realized": pf.get("realizedPnl"),
            "unrealized": pf.get("unrealizedPnl"),
            "ret_pct": pf.get("totalReturnPct"),
            "positions": pf.get("positionsUsed"),
            "starting": pf.get("startingCapital"),
        }
    except Exception:
        return None


def collect_equity_series(runs_dir: Path = RUNS_DIR) -> list[dict]:
    """One point per run date: the day's latest snapshot (by snapshot_time)."""
    series = []
    if not runs_dir.is_dir():
        return series
    for day_dir in sorted(runs_dir.iterdir()):
        if not day_dir.is_dir() or not DATE_RE.match(day_dir.name):
            continue
        candidates = []
        legacy = day_dir / "input" / "positions_snapshot.json"
        if legacy.exists():
            candidates.append(legacy)
        for slot_dir in day_dir.iterdir():
            slotted = slot_dir / "input" / "positions_snapshot.json"
            if slot_dir.is_dir() and slotted.exists():
                candidates.append(slotted)
        points = [p for p in (_snapshot_point(c) for c in candidates) if p]
        if not points:
            continue
        best = max(points, key=lambda p: p["time"])
        best["date"] = day_dir.name
        series.append(best)
    return series


def inception_point(tracking_dir: Path = TRACKING_DIR) -> dict | None:
    """The one pre-snapshot fact we can state: at portfolio creation
    (portfolio_config.created) equity was exactly starting_capital."""
    try:
        cfg = _read_json(tracking_dir / "portfolio_config.json")
        created = cfg.get("created")
        starting = cfg.get("starting_capital")
        if created and starting:
            return {"date": created, "time": "", "equity": float(starting),
                    "ret_pct": 0.0, "positions": 0, "starting": starting,
                    "synthetic": True}
    except Exception:
        pass
    return None


def load_active(tracking_dir: Path = TRACKING_DIR) -> dict:
    try:
        return _read_json(tracking_dir / "positions.json")
    except Exception:
        return {"portfolio": {}, "activePositions": []}


def load_closed_trades(tracking_dir: Path = TRACKING_DIR) -> list[dict]:
    trades = []
    closed = tracking_dir / "closed"
    if not closed.is_dir():
        return trades
    for f in sorted(closed.glob("*.json")):
        try:
            p = _read_json(f)
            if p.get("exitDate") and p.get("returnPct") is not None:
                trades.append(p)
        except Exception:
            pass
    trades.sort(key=lambda t: t.get("exitDate", ""), reverse=True)
    return trades


def compute_stats(series: list[dict], trades: list[dict]) -> dict:
    stats = {}
    if series:
        equities = [p["equity"] for p in series if p["equity"]]
        peak, max_dd = float("-inf"), 0.0
        for e in equities:
            peak = max(peak, e)
            if peak > 0:
                max_dd = max(max_dd, (peak - e) / peak * 100)
        stats["max_drawdown_pct"] = round(max_dd, 2)
    wins = [t for t in trades if t["returnPct"] > 0]
    losses = [t for t in trades if t["returnPct"] <= 0]
    stats["n_trades"] = len(trades)
    stats["n_wins"] = len(wins)
    stats["win_rate"] = round(len(wins) / len(trades) * 100, 1) if trades else None
    stats["avg_win"] = round(sum(t["returnPct"] for t in wins) / len(wins), 2) if wins else None
    stats["avg_loss"] = round(sum(t["returnPct"] for t in losses) / len(losses), 2) if losses else None
    gross_win = sum(t["returnPct"] for t in wins)
    gross_loss = abs(sum(t["returnPct"] for t in losses))
    stats["profit_factor"] = round(gross_win / gross_loss, 2) if gross_loss else None
    return stats


def _fmt_money(v) -> str:
    return f"{v:,.0f}" if isinstance(v, (int, float)) else "—"


def _pnl_cls(v) -> str:
    if not isinstance(v, (int, float)) or v == 0:
        return "flat"
    return "up" if v > 0 else "down"  # up=red, down=green (A-share)


def _pct(v, signed=True) -> str:
    if not isinstance(v, (int, float)):
        return "—"
    return f"{v:+.2f}%" if signed else f"{v:.2f}%"


def render_html(series, active, trades, stats, generated_at=None) -> str:
    pf = active.get("portfolio", {})
    positions = active.get("activePositions", [])
    generated_at = generated_at or datetime.now().astimezone().isoformat(timespec="seconds")

    chart_data = [
        {"d": p["date"], "e": round(p["equity"], 0), "r": p.get("ret_pct"),
         "n": p.get("positions"), **({"s": 1} if p.get("synthetic") else {})}
        for p in series if isinstance(p.get("equity"), (int, float))
    ]
    starting = (series[-1].get("starting") if series else None) or pf.get("startingCapital") or 1000000

    cards = [
        ("总资产", _fmt_money(pf.get("totalEquity")), _pnl_cls(pf.get("totalPnl"))),
        ("总收益率", _pct(pf.get("totalReturnPct")), _pnl_cls(pf.get("totalReturnPct"))),
        ("今日盈亏", _fmt_money(pf.get("dayPnl")), _pnl_cls(pf.get("dayPnl"))),
        ("已实现盈亏", _fmt_money(pf.get("realizedPnl")), _pnl_cls(pf.get("realizedPnl"))),
        ("未实现盈亏", _fmt_money(pf.get("unrealizedPnl")), _pnl_cls(pf.get("unrealizedPnl"))),
        ("现金占比", _pct(pf.get("cashPct"), signed=False), "flat"),
        ("最大回撤", _pct(stats.get("max_drawdown_pct"), signed=False), "down" if stats.get("max_drawdown_pct") else "flat"),
        ("持仓", f"{pf.get('positionsUsed', '—')}/{pf.get('positionsMax', '—')}", "flat"),
    ]
    cards_html = "\n".join(
        f'<div class="card"><div class="label">{html.escape(k)}</div>'
        f'<div class="value {cls}">{html.escape(str(v))}</div></div>'
        for k, v, cls in cards
    )

    pos_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(p.get('code', ''))}</td>"
        f"<td>{html.escape(p.get('name', ''))}</td>"
        f"<td>{html.escape(p.get('entryDate', ''))}</td>"
        f"<td class='num'>{p.get('entryPrice', '—')}</td>"
        f"<td class='num'>{p.get('currentPrice', '—')}</td>"
        f"<td class='num {_pnl_cls(p.get('pnl_pct'))}'>{_pct(p.get('pnl_pct'))}</td>"
        f"<td class='num'>{p.get('currentStop', '—')}</td>"
        f"<td class='num'>{_pct(p.get('weight_pct'), signed=False)}</td>"
        f"<td>{html.escape(p.get('sector', '') or '')}</td>"
        "</tr>"
        for p in sorted(positions, key=lambda x: -(x.get("pnl_pct") or 0))
    ) or "<tr><td colspan='9' class='empty'>当前空仓</td></tr>"

    trade_rows = "\n".join(
        "<tr>"
        f"<td>{html.escape(t.get('code', ''))}</td>"
        f"<td>{html.escape(t.get('name', ''))}</td>"
        f"<td>{html.escape(t.get('entryDate', ''))}</td>"
        f"<td>{html.escape(t.get('exitDate', ''))}</td>"
        f"<td class='num'>{t.get('holdingDays', '—')}</td>"
        f"<td class='num {_pnl_cls(t.get('returnPct'))}'>{_pct(t.get('returnPct'))}</td>"
        f"<td>{html.escape(str(t.get('exitReason', '') or ''))}</td>"
        "</tr>"
        for t in trades
    ) or "<tr><td colspan='7' class='empty'>暂无已平仓交易</td></tr>"

    win_summary = (
        f"共 {stats['n_trades']} 笔 · 胜率 {stats['win_rate']}% ({stats['n_wins']}胜) · "
        f"平均盈利 {_pct(stats['avg_win'])} · 平均亏损 {_pct(stats['avg_loss'])} · "
        f"盈亏比 {stats['profit_factor'] if stats['profit_factor'] is not None else '—'}"
        if stats.get("n_trades") else "暂无已平仓交易"
    )

    data_json = json.dumps(chart_data, ensure_ascii=False)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>组合总览 · 模拟盘</title>
<style>
  :root {{ --up:#d43a3a; --down:#1a9c62; --fg:#1c2330; --muted:#6b7482;
           --line:#e4e8ee; --bg:#f6f7f9; --card:#fff; }}
  * {{ box-sizing:border-box; }}
  body {{ margin:0; font:14px/1.55 -apple-system,"PingFang SC","Microsoft YaHei",sans-serif;
          color:var(--fg); background:var(--bg); }}
  .wrap {{ max-width:1080px; margin:0 auto; padding:28px 20px 48px; }}
  h1 {{ font-size:21px; margin:0 0 2px; }}
  .sub {{ color:var(--muted); font-size:12.5px; margin-bottom:20px; }}
  h2 {{ font-size:15.5px; margin:30px 0 10px; }}
  .cards {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(122px,1fr)); gap:10px; }}
  .card {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:10px 13px; }}
  .card .label {{ font-size:12px; color:var(--muted); }}
  .card .value {{ font-size:17px; font-weight:600; margin-top:2px; font-variant-numeric:tabular-nums; }}
  .up {{ color:var(--up); }} .down {{ color:var(--down); }} .flat {{ color:var(--fg); }}
  .panel {{ background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }}
  #chart {{ width:100%; height:auto; display:block; }}
  #tip {{ position:fixed; display:none; pointer-events:none; background:#1c2330; color:#fff;
          padding:6px 9px; border-radius:6px; font-size:12px; white-space:nowrap; z-index:9; }}
  table {{ width:100%; border-collapse:collapse; background:var(--card);
           border:1px solid var(--line); border-radius:10px; overflow:hidden; }}
  th,td {{ padding:7px 10px; text-align:left; border-bottom:1px solid var(--line); font-size:13px; }}
  th {{ background:#fafbfc; color:var(--muted); font-weight:500; }}
  tr:last-child td {{ border-bottom:none; }}
  td.num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  td.empty {{ text-align:center; color:var(--muted); padding:18px; }}
  .note {{ color:var(--muted); font-size:12px; margin-top:6px; }}
  footer {{ margin-top:34px; color:var(--muted); font-size:12px; border-top:1px solid var(--line); padding-top:12px; }}
  code {{ background:#eef0f3; padding:1px 5px; border-radius:4px; font-size:11.5px; }}
</style>
</head>
<body>
<div class="wrap">
  <h1>组合总览 <span style="font-weight:400;color:var(--muted);font-size:14px">模拟盘 · A股动量策略</span></h1>
  <div class="sub">生成于 {html.escape(generated_at)} · 红涨绿跌</div>

  <div class="cards">{cards_html}</div>

  <h2>每日总资产</h2>
  <div class="panel">
    <svg id="chart" viewBox="0 0 960 340" preserveAspectRatio="xMidYMid meet"></svg>
    <div class="note">每个交易日取当日最后一次流水线快照的 totalEquity；水平虚线 = 初始资金 {_fmt_money(starting)}。曲线首点为组合起始日（portfolio_config.created，等于初始资金）；起始日至首个每日快照之间无逐日数据，以斜虚线段直连示意。</div>
  </div>
  <div id="tip"></div>

  <h2>当前持仓</h2>
  <table>
    <thead><tr><th>代码</th><th>名称</th><th>建仓日</th><th style="text-align:right">成本</th>
    <th style="text-align:right">现价</th><th style="text-align:right">盈亏</th>
    <th style="text-align:right">止损</th><th style="text-align:right">权重</th><th>板块</th></tr></thead>
    <tbody>{pos_rows}</tbody>
  </table>

  <h2>已平仓交易</h2>
  <div class="note" style="margin:0 0 8px">{html.escape(win_summary)}</div>
  <table>
    <thead><tr><th>代码</th><th>名称</th><th>建仓日</th><th>平仓日</th>
    <th style="text-align:right">持有天数</th><th style="text-align:right">收益</th><th>平仓原因</th></tr></thead>
    <tbody>{trade_rows}</tbody>
  </table>

  <footer>
    数据来源〔内部数据〕: <code>runs/*/input/positions_snapshot.json</code>（资产曲线）·
    <code>tracking/positions.json</code>（持仓）· <code>tracking/closed/</code>（历史交易）。
    重新生成: <code>python3 scripts/build_site.py</code>
  </footer>
</div>

<script>
const DATA = {data_json};
const STARTING = {json.dumps(starting)};
(function() {{
  const svg = document.getElementById("chart"), tip = document.getElementById("tip");
  if (!DATA.length) {{ svg.outerHTML = "<div class='empty'>暂无快照数据</div>"; return; }}
  const W = 960, H = 340, L = 74, R = 16, T = 16, B = 34;
  const iw = W - L - R, ih = H - T - B;
  const es = DATA.map(p => p.e);
  let lo = Math.min(...es, STARTING), hi = Math.max(...es, STARTING);
  const pad = (hi - lo) * 0.06 || 1; lo -= pad; hi += pad;
  const x = i => L + (DATA.length === 1 ? iw / 2 : i * iw / (DATA.length - 1));
  const y = v => T + (hi - v) / (hi - lo) * ih;
  const S = [];
  // gridlines + y labels
  for (let g = 0; g <= 4; g++) {{
    const v = lo + (hi - lo) * g / 4, yy = y(v);
    S.push(`<line x1="${{L}}" y1="${{yy}}" x2="${{W - R}}" y2="${{yy}}" stroke="#eef1f5"/>`);
    S.push(`<text x="${{L - 8}}" y="${{yy + 4}}" text-anchor="end" font-size="11" fill="#8a93a2">${{Math.round(v).toLocaleString()}}</text>`);
  }}
  // x labels: ~8 ticks
  const step = Math.max(1, Math.round(DATA.length / 8));
  for (let i = 0; i < DATA.length; i += step) {{
    S.push(`<text x="${{x(i)}}" y="${{H - 10}}" text-anchor="middle" font-size="11" fill="#8a93a2">${{DATA[i].d.slice(5)}}</text>`);
  }}
  // baseline
  S.push(`<line x1="${{L}}" y1="${{y(STARTING)}}" x2="${{W - R}}" y2="${{y(STARTING)}}" stroke="#9aa3b2" stroke-dasharray="5 4"/>`);
  // area + line (blue neutral line; fill tinted by end-vs-start).
  // A leading synthetic inception point (p.s) gets a DASHED connector —
  // there are no daily snapshots between inception and the first real one.
  const pts = DATA.map((p, i) => `${{x(i).toFixed(1)}},${{y(p.e).toFixed(1)}}`).join(" ");
  const last = DATA[DATA.length - 1].e;
  const tone = last >= STARTING ? "212,58,58" : "26,156,98";
  S.push(`<polygon points="${{L}},${{y(STARTING)}} ${{pts}} ${{x(DATA.length - 1)}},${{y(STARTING)}}" fill="rgba(${{tone}},0.07)"/>`);
  const solidFrom = (DATA[0].s && DATA.length > 1) ? 1 : 0;
  if (solidFrom) {{
    S.push(`<line x1="${{x(0)}}" y1="${{y(DATA[0].e)}}" x2="${{x(1)}}" y2="${{y(DATA[1].e)}}" stroke="#3b6ea5" stroke-width="2" stroke-dasharray="6 5"/>`);
  }}
  const solidPts = DATA.slice(solidFrom).map((p, i) => `${{x(i + solidFrom).toFixed(1)}},${{y(p.e).toFixed(1)}}`).join(" ");
  S.push(`<polyline points="${{solidPts}}" fill="none" stroke="#3b6ea5" stroke-width="2"/>`);
  S.push(`<circle id="dot" r="4" fill="#3b6ea5" stroke="#fff" stroke-width="1.5" style="display:none"/>`);
  S.push(`<line id="guide" y1="${{T}}" y2="${{T + ih}}" stroke="#c3cad4" stroke-dasharray="3 3" style="display:none"/>`);
  svg.innerHTML = S.join("");
  const dot = svg.querySelector("#dot"), guide = svg.querySelector("#guide");
  svg.addEventListener("mousemove", ev => {{
    const r = svg.getBoundingClientRect();
    const mx = (ev.clientX - r.left) * W / r.width;
    let i = Math.round((mx - L) / (iw / Math.max(DATA.length - 1, 1)));
    i = Math.max(0, Math.min(DATA.length - 1, i));
    const p = DATA[i];
    dot.setAttribute("cx", x(i)); dot.setAttribute("cy", y(p.e)); dot.style.display = "";
    guide.setAttribute("x1", x(i)); guide.setAttribute("x2", x(i)); guide.style.display = "";
    tip.style.display = "block";
    tip.style.left = (ev.clientX + 14) + "px"; tip.style.top = (ev.clientY - 12) + "px";
    if (p.s) {{
      tip.textContent = `${{p.d}} · ${{p.e.toLocaleString()}} · 组合起始(初始资金)`;
    }} else {{
      const ret = p.r == null ? "" : ` · ${{p.r >= 0 ? "+" : ""}}${{p.r}}%`;
      tip.textContent = `${{p.d}} · ${{p.e.toLocaleString()}}${{ret}} · ${{p.n ?? "?"}}仓`;
    }}
  }});
  svg.addEventListener("mouseleave", () => {{
    dot.style.display = "none"; guide.style.display = "none"; tip.style.display = "none";
  }});
}})();
</script>
</body>
</html>
"""


def build(site_dir: Path = SITE_DIR) -> Path:
    series = collect_equity_series()
    anchor = inception_point()
    if anchor and (not series or anchor["date"] < series[0]["date"]):
        series.insert(0, anchor)
    active = load_active()
    trades = load_closed_trades()
    stats = compute_stats(series, trades)
    site_dir.mkdir(parents=True, exist_ok=True)
    out = site_dir / "index.html"
    out.write_text(render_html(series, active, trades, stats), encoding="utf-8")
    print(f"[site] {out} — {len(series)} equity points, "
          f"{len(active.get('activePositions', []))} positions, {len(trades)} closed trades",
          file=sys.stderr)
    return out


if __name__ == "__main__":
    build()
