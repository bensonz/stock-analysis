#!/usr/bin/env python3
"""Test Eastmoney push2 connectivity."""
import requests

HOSTS = [
    "push2.eastmoney.com",
    "82.push2.eastmoney.com",
    "48.push2.eastmoney.com",
    "17.push2.eastmoney.com",
]

params = {
    "pn": 1, "pz": 5, "po": 1, "np": 1,
    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
    "fltt": 2, "invt": 2, "fid": "f12",
    "fs": "m:1+t:1",
    "fields": "f2,f3,f12,f14",
}

for host in HOSTS:
    url = f"https://{host}/api/qt/clist/get"
    try:
        r = requests.get(url, params=params, timeout=10)
        print(f"✅ {host}: HTTP {r.status_code}, {len(r.text)} bytes")
    except Exception as e:
        err = str(e).split("(Caused by")[0].strip() if "(Caused by" in str(e) else str(e)[:80]
        print(f"❌ {host}: {err}")
