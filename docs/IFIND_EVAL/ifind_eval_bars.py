"""Diff iFinD daily bars against the local pricedb over a recent window."""
import json, sqlite3, time, requests

DB = "/Users/bz/Work/Personal/stock-analysis/data/pricedb/ashare_prices.db"
BASE = "https://quantapi.51ifind.com/api/v1/"
AT = open('/tmp/ifind_at.txt').read().strip()
H = {"Content-Type": "application/json", "access_token": AT}
BEG, END = "2026-08-11", "2026-08-25"

con = sqlite3.connect(DB)
# stratified sample: spread across the universe by code, only actively-traded names
codes = [r[0] for r in con.execute(
    "SELECT code FROM stocks WHERE code IN "
    "(SELECT code FROM daily_prices WHERE date=? ) ORDER BY code", (END,)).fetchall()]
sample = codes[::max(1, len(codes)//120)][:120]
print(f"universe with {END} bar: {len(codes)}, sampling {len(sample)}")

def ths(code):
    sfx = ".SH" if code.startswith(('6', '9')) else (".BJ" if code.startswith(('4', '8')) else ".SZ")
    return code + sfx

results, vol_total, t0 = [], 0, time.time()
BATCH = 20
for i in range(0, len(sample), BATCH):
    chunk = sample[i:i+BATCH]
    r = requests.post(BASE + "cmd_history_quotation", headers=H, timeout=90, json={
        "codes": ",".join(ths(c) for c in chunk),
        "indicators": "open,high,low,close,volume,amount",
        "startdate": BEG, "enddate": END, "functionpara": {"Fill": "Original"}})
    j = r.json()
    if j.get('errorcode'):
        print("ERR", j.get('errorcode'), j.get('errmsg')); break
    vol_total += j.get('dataVol', 0) or 0
    for tb in j.get('tables', []):
        code = tb['thscode'].split('.')[0]
        t = tb['table']
        for k, d in enumerate(tb['time']):
            results.append((code, d, t['open'][k], t['high'][k], t['low'][k],
                            t['close'][k], t['volume'][k], t['amount'][k]))
elapsed = time.time() - t0
print(f"fetched {len(results)} bars for {len(sample)} codes in {elapsed:.1f}s, dataVol={vol_total}")

# compare
stats = dict(matched=0, close_mismatch=0, missing_local=0, missing_ifind=0,
             amount_null_local=0, amount_null_ifind=0, ohlc_mismatch=0)
examples = []
for code, d, o, h, l, c, v, amt in results:
    row = con.execute("SELECT open,high,low,close,volume,amount FROM daily_prices "
                      "WHERE code=? AND date=?", (code, d)).fetchone()
    if row is None:
        stats['missing_local'] += 1
        if len(examples) < 12: examples.append(("LOCAL-MISSING", code, d, c, None))
        continue
    lo, lh, ll, lc, lv, lamt = row
    if c is None or lc is None:
        stats['missing_ifind'] += 1; continue
    if abs(c - lc) > max(0.011, abs(lc) * 0.0005):
        stats['close_mismatch'] += 1
        if len(examples) < 12: examples.append(("CLOSE", code, d, c, lc))
    else:
        stats['matched'] += 1
    if any(x is not None and y is not None and abs(x-y) > max(0.011, abs(y)*0.0005)
           for x, y in ((o, lo), (h, lh), (l, ll))):
        stats['ohlc_mismatch'] += 1
    if lamt is None: stats['amount_null_local'] += 1
    if amt is None: stats['amount_null_ifind'] += 1

# local bars iFind didn't return
local_n = con.execute("SELECT COUNT(*) FROM daily_prices WHERE date BETWEEN ? AND ? "
                      "AND code IN (%s)" % ",".join("?"*len(sample)),
                      (BEG, END, *sample)).fetchone()[0]
print("\n--- BAR COMPARISON", BEG, "→", END, "---")
print(f"iFinD bars returned : {len(results)}")
print(f"local bars in window: {local_n}")
for k, v in stats.items(): print(f"{k:20}: {v}")
print("\nexamples:", json.dumps(examples, ensure_ascii=False))
