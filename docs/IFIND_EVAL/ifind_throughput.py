"""Universe-scale throughput + adjustment-factor probe."""
import sqlite3, time, requests, json
from concurrent.futures import ThreadPoolExecutor

DB = "/Users/bz/Work/Personal/stock-analysis/data/pricedb/ashare_prices.db"
BASE = "https://quantapi.51ifind.com/api/v1/"
AT = open('/tmp/ifind_at.txt').read().strip()
H = {"Content-Type": "application/json", "access_token": AT}

con = sqlite3.connect(DB)
codes = [r[0] for r in con.execute(
    "SELECT DISTINCT code FROM daily_prices WHERE date='2026-08-25' ORDER BY code")]
def ths(c):
    return c + (".SH" if c.startswith(('6','9')) else ".BJ" if c.startswith(('4','8')) else ".SZ")
uni = [ths(c) for c in codes]
print(f"universe: {len(uni)} codes")

def fetch(chunk, day="2026-08-25"):
    r = requests.post(BASE+"cmd_history_quotation", headers=H, timeout=120, json={
        "codes": ",".join(chunk),
        "indicators": "open,high,low,close,volume,amount,changeRatio,turnoverRatio",
        "startdate": day, "enddate": day, "functionpara": {"Fill": "Original"}})
    return r.json()

# --- batch-size limit probe ---
print("\n--- max codes per request ---")
for n in (50, 100, 200, 400, 800):
    j = fetch(uni[:n]); got = len(j.get('tables') or [])
    print(f"  request {n:4} codes -> errorcode={j.get('errorcode')} tables={got} dataVol={j.get('dataVol')} perf={j.get('perf')}ms")
    if j.get('errorcode'): print("     errmsg:", j.get('errmsg')); break

# --- full universe, parallel ---
print("\n--- full universe single-day pull ---")
CH = 200
chunks = [uni[i:i+CH] for i in range(0, len(uni), CH)]
t0 = time.time(); rows = 0; vol = 0; errs = []
with ThreadPoolExecutor(max_workers=6) as ex:
    for j in ex.map(fetch, chunks):
        if j.get('errorcode'): errs.append((j.get('errorcode'), j.get('errmsg'))); continue
        vol += j.get('dataVol') or 0
        rows += len(j.get('tables') or [])
el = time.time()-t0
print(f"  {rows}/{len(uni)} codes in {el:.1f}s  dataVol={vol}  errors={errs[:3]} ({len(errs)} chunks failed)")

# --- adjustment factor availability ---
print("\n--- 复权因子 / adjusted close ---")
r = requests.post(BASE+"basic_data_service", headers=H, timeout=60, json={
    "codes": "600519.SH,000001.SZ",
    "indipara": [{"indicator": "ths_adjust_factor_stock", "indiparams": ["2026-08-25"]}]})
print("  ths_adjust_factor_stock:", json.dumps(r.json(), ensure_ascii=False)[:400])

for para in ({"CPS": "1"}, {"CPS": "2"}, {}):
    r = requests.post(BASE+"cmd_history_quotation", headers=H, timeout=60, json={
        "codes": "600519.SH", "indicators": "close",
        "startdate": "2026-08-18", "enddate": "2026-08-25", "functionpara": para})
    j = r.json()
    t = (j.get('tables') or [{}])[0].get('table', {})
    print(f"  functionpara={para} -> close={t.get('close')}")
