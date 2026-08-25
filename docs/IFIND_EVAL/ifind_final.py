import requests, json, sqlite3
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))
import ifind_client
AT = ifind_client.get_client().access_token()
H = {"Content-Type": "application/json", "access_token": AT}
BASE = "https://quantapi.51ifind.com/api/v1/"
con = sqlite3.connect("/Users/bz/Work/Personal/stock-analysis/data/pricedb/ashare_prices.db")
def ths(c): return c + (".SH" if c.startswith(('6','9')) else ".BJ" if c.startswith(('4','8')) else ".SZ")

print("=== 1. adjustment-factor step comparison (2026-08-25 ex-div names) ===")
rows = con.execute("""with f as (select code,date,factor, lag(factor) over (partition by code order by date) pf
    from adj_factors where date>='2026-07-01')
    select code,date,pf,factor from f where pf is not null and abs(factor-pf)>1e-9 and date='2026-08-25'""").fetchall()
j = requests.post(BASE+"date_sequence", headers=H, timeout=60, json={
    "codes": ",".join(ths(r[0]) for r in rows),
    "indipara": [{"indicator": "ths_af_stock", "indiparams": [""]}],
    "functionpara": {"Fill": "Original"}, "startdate": "2026-08-21", "enddate": "2026-08-25"}).json()
ifd = {t['thscode'].split('.')[0]: (t['time'], t['table']['ths_af_stock']) for t in j.get('tables', [])}
print(f"  {'code':8} {'local step':>12} {'iFind step':>12} {'diff bp':>9}")
for code, d, pf, fac in rows:
    times, afs = ifd.get(code, ([], []))
    if len(afs) < 2 or afs[-1] is None or afs[-2] is None: print(f"  {code:8} (no iFind af)"); continue
    ls, isp = fac/pf, afs[-1]/afs[-2]
    print(f"  {code:8} {ls:12.6f} {isp:12.6f} {(isp-ls)*10000:9.2f}")

print("\n=== 2. real-time snapshot vs local close (universe sample) ===")
codes = [r[0] for r in con.execute("select distinct code from daily_prices where date='2026-08-25' order by code")][::40][:150]
j = requests.post(BASE+"real_time_quotation", headers=H, timeout=90, json={
    "codes": ",".join(ths(c) for c in codes), "indicators": "latest,open,high,low,preClose,volume,amount"}).json()
print(f"  ec={j.get('errorcode')} returned={len(j.get('tables') or [])}/{len(codes)} dataVol={j.get('dataVol')}")
mis = 0; nulls = 0
for t in j.get('tables', []):
    c = t['thscode'].split('.')[0]; lt = t['table']['latest'][0]
    row = con.execute("select close from daily_prices where code=? and date='2026-08-25'", (c,)).fetchone()
    if lt is None or row is None or row[0] is None: nulls += 1; continue
    if abs(lt-row[0]) > max(0.011, row[0]*0.0005): mis += 1
print(f"  latest vs local close: mismatches={mis} unusable={nulls} of {len(j.get('tables') or [])}")

print("\n=== 3. index / breadth data ===")
j = requests.post(BASE+"cmd_history_quotation", headers=H, timeout=60, json={
    "codes": "000001.SH,399001.SZ,399006.SZ,000688.SH",
    "indicators": "open,high,low,close,volume,amount,changeRatio",
    "startdate": "2026-08-21", "enddate": "2026-08-25", "functionpara": {"Fill": "Original"}}).json()
print(f"  ec={j.get('errorcode')} indices={[t['thscode'] for t in j.get('tables', [])]}")
for t in j.get('tables', [])[:2]:
    print(f"    {t['thscode']} close={t['table']['close']} chg={[round(x,2) for x in t['table']['changeRatio']]}")

print("\n=== 4. industry / sector membership ===")
j = requests.post(BASE+"basic_data_service", headers=H, timeout=60, json={
    "codes": "600519.SH,300750.SZ", "indipara": [
        {"indicator": "ths_the_industry_index_stock", "indiparams": ["2026-08-25"]},
        {"indicator": "ths_thslv1_name_stock", "indiparams": [""]},
        {"indicator": "ths_thslv2_name_stock", "indiparams": [""]},
        {"indicator": "ths_total_market_value_stock", "indiparams": ["2026-08-25"]},
        {"indicator": "ths_free_float_market_value_stock", "indiparams": ["2026-08-25"]}]}).json()
print("  ec=", j.get('errorcode'), json.dumps(j.get('tables'), ensure_ascii=False)[:600])

print("\n=== 5. history depth (how far back?) ===")
for beg, end in [("2015-01-05", "2015-01-09"), ("2005-01-04", "2005-01-07")]:
    j = requests.post(BASE+"cmd_history_quotation", headers=H, timeout=60, json={
        "codes": "600519.SH", "indicators": "close", "startdate": beg, "enddate": end,
        "functionpara": {"Fill": "Original"}}).json()
    t = (j.get('tables') or [{}])[0].get('table', {})
    print(f"  {beg}: ec={j.get('errorcode')} close={t.get('close')}")
