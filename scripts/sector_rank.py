"""申万二级 sector momentum ranking for ANALYST.md Rule 1 and the Sector
Momentum Overlay (added 2026-11-21).

The rules ask for every sector ranked by 5-day (and 20-day) performance:
buy only in the top 30%, sell a holding whose sector sits in the bottom 30%
for 3+ days. Until now the prompt carried only today's top-5/bottom-5 by
1-day change, so neither test could be done (11-03 audit, issue 4).

How it is computed — locally, so it covers every sector and has history from
day one:
- Membership: akshare `sw_index_second_info` + `index_component_sw`, cached in
  data/sw_l2_members.json and refreshed every MEMBERS_MAX_AGE_DAYS (~3 min).
- Return: equal-weighted mean of the members' adjusted-close returns from the
  local price DB. NOT the official (cap-weighted) 申万 index, so it can
  differ from the 1-day top-5 line, which comes from a different feed.
- Reference date: the latest settled session (rps_calculator's resolver never
  picks the open session), so a noon run ranks as of the previous close.
"""
import json
import math
import sqlite3
from datetime import date as _date
from pathlib import Path

import akshare as ak

import price_adjust
from rps_calculator import _load_trading_dates, _resolve_reference_date

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "pricedb" / "ashare_prices.db"
MEMBERS_CACHE = PROJECT_ROOT / "data" / "sw_l2_members.json"
MEMBERS_MAX_AGE_DAYS = 30
BAND_PCT = 0.30        # ANALYST.md: top 30% to enter, bottom 30% is "cold"
WINDOW = 5             # sessions for the ranking return
LONG_WINDOW = 20       # sessions for the context return
COLD_LOOKBACK = 10     # sessions scanned when counting consecutive cold days
MIN_MEMBERS = 3        # a sector with fewer priced members on a day is unranked
TOP_N = 10             # sectors listed at each end in the prompt
BASIS = "申万二级, 成分股等权5日涨幅 (本地价格库, 复权); 非官方指数"


def refresh_members() -> dict:
    """{sector_code: {name, parent, codes}} for every 申万二级 sector."""
    info = ak.sw_index_second_info()
    sectors = {}
    for _, row in info.iterrows():
        code = str(row["行业代码"]).split(".")[0]
        members = ak.index_component_sw(symbol=code)
        sectors[code] = {"name": str(row["行业名称"]), "parent": str(row["上级行业"]),
                         "codes": sorted(str(c).zfill(6) for c in members["证券代码"])}
    return sectors


def load_members(today: str, cache: Path = MEMBERS_CACHE,
                 refresh=refresh_members) -> tuple[dict, str | None]:
    """(sectors, note). Refreshes a missing or stale cache; when the refresh
    fails, an old cache is used and `note` says so. No cache and no refresh
    raises — there is nothing honest to rank with."""
    cached = json.loads(cache.read_text(encoding="utf-8")) if cache.exists() else None
    if cached:
        age = (_date.fromisoformat(today) - _date.fromisoformat(cached["fetched"])).days
        if age <= MEMBERS_MAX_AGE_DAYS:
            return cached["sectors"], None
    try:
        sectors = refresh()
        if len(sectors) < 100:
            raise ValueError(f"only {len(sectors)} sectors returned")
    except Exception as e:
        if cached:
            return cached["sectors"], f"成分表刷新失败, 沿用 {cached['fetched']} 版本: {e}"
        raise
    cache.write_text(json.dumps({"fetched": today, "sectors": sectors},
                                ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return sectors, None


def _band(rank: int, n: int) -> str:
    edge = math.ceil(BAND_PCT * n)
    if rank <= edge:
        return "hot"
    if rank > n - edge:
        return "cold"
    return "mid"


def rank_sectors(conn: sqlite3.Connection, sectors: dict, asof: str | None = None) -> dict | None:
    """Rank every sector by equal-weighted WINDOW-session return on each of the
    last COLD_LOOKBACK sessions; report today's rank, band, 20-session return
    and consecutive cold sessions. None when the DB has too little history."""
    ref = _resolve_reference_date(conn, asof)
    if not ref:
        return None
    need = max(LONG_WINDOW + 1, COLD_LOOKBACK + WINDOW)
    dates = sorted(_load_trading_dates(conn, ref, need))
    if len(dates) < need:
        return None
    price_adjust.ensure_adj_schema(conn)
    closes: dict = {}
    for code, d, px in conn.execute(
            f"SELECT d.code, d.date, {price_adjust.adjusted_close_sql()} "
            f"FROM daily_prices d{price_adjust.adj_join_sql()} "
            "WHERE d.date >= ? AND d.date <= ?", (dates[0], ref)):
        if px and px > 0:
            closes.setdefault(code, {})[d] = px

    def sector_return(members: list, d0: str, d1: str) -> float | None:
        rets = [closes[c][d1] / closes[c][d0] - 1 for c in members
                if d0 in closes.get(c, {}) and d1 in closes.get(c, {})]
        return sum(rets) / len(rets) * 100 if len(rets) >= MIN_MEMBERS else None

    history = []  # per session, oldest first: {sector_code: (rank, band)}
    for i in range(len(dates) - COLD_LOOKBACK, len(dates)):
        rets = {sc: sector_return(s["codes"], dates[i - WINDOW], dates[i])
                for sc, s in sectors.items()}
        ranked = sorted((r, sc) for sc, r in rets.items() if r is not None)[::-1]
        n = len(ranked)
        history.append({sc: (k + 1, _band(k + 1, n), r) for k, (r, sc) in enumerate(ranked)})

    today, n = history[-1], len(history[-1])
    out = {}
    for sc, (rank, band, ret5) in today.items():
        cold_days = 0
        for day in reversed(history):
            if day.get(sc, (None, None))[1] != "cold":
                break
            cold_days += 1
        out[sc] = {"name": sectors[sc]["name"], "rank5": rank, "band": band,
                   "ret5": round(ret5, 2),
                   "ret20": _round(sector_return(sectors[sc]["codes"], dates[-1 - LONG_WINDOW], ref)),
                   "cold_days": cold_days}
    edge = math.ceil(BAND_PCT * n)
    return {"asof": ref, "n": n, "hot_max_rank": edge, "cold_min_rank": n - edge + 1,
            "sectors": out}


def _round(x):
    return None if x is None else round(x, 2)


def for_prompt(ranking: dict, sectors: dict, codes: list) -> dict:
    """The compact block the prompt carries: both ends of the table, and the
    sector, rank and band of each code we hold or might buy."""
    by_rank = sorted(ranking["sectors"].values(), key=lambda s: s["rank5"])
    keep = ("rank5", "name", "ret5", "ret20", "cold_days")
    sector_of = {c: sc for sc, s in sectors.items() for c in s["codes"]}
    stocks = {}
    for code in codes:
        sc = sector_of.get(code)
        s = ranking["sectors"].get(sc) if sc else None
        stocks[code] = ({"sector": s["name"], "rank5": s["rank5"], "band": s["band"],
                         "ret5": s["ret5"], "cold_days": s["cold_days"]} if s
                        else {"sector": sectors[sc]["name"] if sc else None, "band": "unranked"})
    return {"asof": ranking["asof"], "basis": BASIS, "n": ranking["n"],
            "hot": f"rank ≤ {ranking['hot_max_rank']}", "cold": f"rank ≥ {ranking['cold_min_rank']}",
            "top": [{k: s[k] for k in keep} for s in by_rank[:TOP_N]],
            "bottom": [{k: s[k] for k in keep} for s in by_rank[-TOP_N:][::-1]],
            "stocks": stocks}


def collect(codes: list, today: str, db_path: Path = DB_PATH) -> dict:
    """Pipeline entry point. Never raises: a failure comes back as
    {"error": ...} so the prompt says the ranking is missing instead of
    silently dropping it."""
    try:
        sectors, note = load_members(today)
        conn = sqlite3.connect(db_path)
        try:
            ranking = rank_sectors(conn, sectors)
        finally:
            conn.close()
        if not ranking:
            return {"error": "价格库历史不足, 无法计算板块排名"}
        block = for_prompt(ranking, sectors, codes)
        if note:
            block["note"] = note
        return block
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}"}
