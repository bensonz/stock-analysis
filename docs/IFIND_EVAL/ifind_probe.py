import json, sys, requests

BASE = "https://quantapi.51ifind.com/api/v1/"
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2] / "scripts"))
import ifind_client
AT = ifind_client.get_client().access_token()
H = {"Content-Type": "application/json", "access_token": AT}

def call(ep, payload, timeout=60):
    try:
        r = requests.post(BASE + ep, json=payload, headers=H, timeout=timeout)
        try:
            return r.status_code, r.json()
        except Exception:
            return r.status_code, {"_raw": r.text[:400]}
    except Exception as ex:
        return None, {"_err": f"{type(ex).__name__}: {ex}"}

def show(label, ep, payload, full=False):
    st, j = call(ep, payload)
    ec = j.get('errorcode', j.get('errcode'))
    msg = j.get('errmsg', '')
    print(f"\n=== {label}  [{ep}]  http={st} errorcode={ec} errmsg={msg}")
    if j.get('_err') or j.get('_raw'):
        print("   ", j)
        return j
    body = json.dumps(j, ensure_ascii=False)
    print("   ", body if full else body[:900])
    return j

if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
