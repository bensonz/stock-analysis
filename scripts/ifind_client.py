"""iFinD (同花顺 quantapi) HTTP client — internal helper for this repo.

Why this exists
---------------
We hold a paid iFinD seat, and it beat the incumbent akshare→sina chain on every
axis measured in `docs/IFIND_EVAL/FINDINGS.md` (2026-08-25): 1320/1320 bars
matched our pricedb exactly, the full 5207-code universe pulls in 2.4s, and
`amount` is present on 100% of bars where our sina snapshot path writes NULL.

This module is deliberately **standalone** — it imports nothing from the project
so that `pricedb` and `data_collector` can both depend on it without a cycle. The
portable specification lives in `docs/IFIND_EVAL/IFIND_API_GUIDE.md`; other
projects should implement against that guide rather than importing this file.

Payload shapes are not uniform across endpoints and the differences are not
guessable — see the guide. The two that cost the most time to find:

  * `date_sequence` takes ``indipara`` (a list of dicts), NOT ``indicators``.
  * ``ths_the_sw_industry_stock`` takes params ``[level, date]`` — level FIRST.
    Reversed, it returns an empty string rather than an error.
"""

from __future__ import annotations

import contextlib
import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"
TOKEN_CACHE = PROJECT_ROOT / "data" / "ifind_token.json"

BASE_URL = "https://quantapi.51ifind.com/api/v1/"

# Measured clean at 800 codes/request (perf 111ms); 500 leaves headroom.
MAX_CODES_PER_REQUEST = 500
DEFAULT_WORKERS = 6
CALL_TIMEOUT_SEC = float(os.getenv("IFIND_CALL_TIMEOUT", "60"))

# Refresh this long before the server's stated expiry, so a long run cannot
# straddle the boundary mid-flight.
TOKEN_REFRESH_MARGIN = timedelta(hours=6)
# Used only when the server's expired_time is unparseable.
TOKEN_FALLBACK_TTL = timedelta(days=5)

# "no data." — a legitimate empty result (e.g. an empty data_pool), not a fault.
ERRORCODE_NO_DATA = -4001
# "error happen with input parameters" — a wrong indicator name or param order.
# Always a programming error; never degrade silently on it.
ERRORCODE_BAD_PARAMS = -4210


class IFindError(RuntimeError):
    """An iFinD API call returned a non-zero errorcode."""

    def __init__(self, errorcode, errmsg: str, endpoint: str):
        self.errorcode = errorcode
        self.errmsg = errmsg
        self.endpoint = endpoint
        super().__init__(f"iFinD {endpoint} failed: errorcode={errorcode} {errmsg}")


class IFindNotConfigured(RuntimeError):
    """No IFIND_REFRESH_TOKEN available — callers should fall back."""


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


def _read_env_file() -> dict:
    """Parse `.env` into a dict. Duplicated from pricedb to stay import-free."""
    values: dict = {}
    if not ENV_FILE.exists():
        return values
    for raw_line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key:
            values[key] = value.strip().strip('"').strip("'")
    return values


def _env(name: str) -> str | None:
    value = os.getenv(name)
    if value:
        return value.strip()
    value = _read_env_file().get(name)
    return value.strip() if value else None


_PROXY_ENV_KEYS = ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy",
                   "ALL_PROXY", "all_proxy")


@contextlib.contextmanager
def _no_proxy_env():
    """Force DIRECT connections, mirroring pricedb._no_proxy_env.

    Stripping HTTP(S)_PROXY alone is not enough on macOS: requests falls back to
    the *system* proxy config. NO_PROXY='*' wins over both.
    """
    touched = set(_PROXY_ENV_KEYS) | {"NO_PROXY", "no_proxy"}
    saved = {k: os.environ.get(k) for k in touched}
    for k in _PROXY_ENV_KEYS:
        os.environ.pop(k, None)
    forced = os.getenv("IFIND_FORCE_PROXY", "").strip()
    if forced:
        for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy"):
            os.environ[k] = forced
        os.environ.pop("NO_PROXY", None)
        os.environ.pop("no_proxy", None)
    else:
        os.environ["NO_PROXY"] = "*"
        os.environ["no_proxy"] = "*"
    try:
        yield
    finally:
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ---------------------------------------------------------------------------
# Code formatting
# ---------------------------------------------------------------------------


def to_ths_code(code: str, exchange: str | None = None) -> str:
    """Convert a bare 6-digit A-share code to iFinD's ``600519.SH`` form.

    Prefers an explicit exchange (pricedb's `stocks.exchange`); falls back to
    board prefixes. Note 688xxx (STAR) is SH, so the '6' test must precede the
    '8' test for BJ.
    """
    code = str(code).strip()
    if "." in code:
        return code.upper()
    if exchange:
        ex = exchange.strip().upper()
        if ex in {"SH", "SSE"}:
            return f"{code}.SH"
        if ex in {"SZ", "SZSE"}:
            return f"{code}.SZ"
        if ex in {"BJ", "BSE"}:
            return f"{code}.BJ"
    if code.startswith(("60", "68", "90", "11", "13")):
        return f"{code}.SH"
    if code.startswith(("43", "83", "87", "88", "92")):
        return f"{code}.BJ"
    return f"{code}.SZ"


def from_ths_code(thscode: str) -> str:
    """``600519.SH`` → ``600519``."""
    return str(thscode).split(".")[0]


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


class IFindClient:
    """Thin, thread-safe wrapper over the iFinD HTTP API.

    Tokens: a refresh token (long-lived, from `.env`) is exchanged for an access
    token valid ~7 days, cached on disk so repeated CLI invocations don't burn a
    round trip each. Token values are never logged.
    """

    def __init__(self, refresh_token: str | None = None,
                 token_cache: Path | None = None):
        self._refresh_token = refresh_token or _env("IFIND_REFRESH_TOKEN")
        self._token_cache = Path(token_cache) if token_cache else TOKEN_CACHE
        self._access: str | None = None
        self._expires: datetime | None = None
        self._lock = threading.Lock()
        self.data_vol = 0

    # -- auth ------------------------------------------------------------

    @property
    def configured(self) -> bool:
        return bool(self._refresh_token)

    def _load_cached_token(self) -> bool:
        try:
            blob = json.loads(self._token_cache.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return False
        token, expires = blob.get("access_token"), blob.get("expires_at")
        if not token or not expires:
            return False
        try:
            expires_dt = datetime.fromisoformat(expires)
        except ValueError:
            return False
        if datetime.now() >= expires_dt - TOKEN_REFRESH_MARGIN:
            return False
        self._access, self._expires = token, expires_dt
        return True

    def _store_token(self, token: str, expired_time: str | None):
        try:
            expires_dt = datetime.strptime(expired_time or "", "%Y-%m-%d %H:%M:%S")
        except ValueError:
            expires_dt = datetime.now() + TOKEN_FALLBACK_TTL
        self._access, self._expires = token, expires_dt
        try:
            self._token_cache.parent.mkdir(parents=True, exist_ok=True)
            self._token_cache.write_text(
                json.dumps({"access_token": token,
                            "expires_at": expires_dt.isoformat()}),
                encoding="utf-8")
            os.chmod(self._token_cache, 0o600)
        except OSError as e:
            print(f"  [ifind] could not cache token: {e}", file=sys.stderr)

    def _refresh(self) -> str:
        import requests
        with _no_proxy_env():
            resp = requests.post(
                BASE_URL + "get_access_token",
                headers={"ContentType": "application/json",
                         "refresh_token": self._refresh_token},
                timeout=CALL_TIMEOUT_SEC)
        payload = resp.json()
        if payload.get("errorcode"):
            raise IFindError(payload.get("errorcode"), payload.get("errmsg", ""),
                             "get_access_token")
        data = payload.get("data") or {}
        token = data.get("access_token")
        if not token:
            raise IFindError(-1, "no access_token in response", "get_access_token")
        self._store_token(token, data.get("expired_time"))
        return token

    def access_token(self) -> str:
        if not self.configured:
            raise IFindNotConfigured(
                "IFIND_REFRESH_TOKEN is not set (checked env and .env)")
        with self._lock:
            if self._access and self._expires and \
                    datetime.now() < self._expires - TOKEN_REFRESH_MARGIN:
                return self._access
            if self._load_cached_token():
                return self._access
            return self._refresh()

    # -- transport -------------------------------------------------------

    def post(self, endpoint: str, payload: dict, _retry: bool = True) -> dict:
        """POST to an endpoint and return the parsed body.

        Raises IFindError on a non-zero errorcode, except ERRORCODE_NO_DATA
        which is a legitimate empty result and comes back as an empty payload.
        """
        import requests
        headers = {"Content-Type": "application/json",
                   "access_token": self.access_token()}
        with _no_proxy_env():
            resp = requests.post(BASE_URL + endpoint, json=payload,
                                 headers=headers, timeout=CALL_TIMEOUT_SEC)
        if resp.status_code == 404:
            raise IFindError(404, f"no such endpoint (HTTP 404)", endpoint)
        try:
            body = resp.json()
        except ValueError:
            raise IFindError(resp.status_code,
                             f"unparseable response: {resp.text[:200]}", endpoint)

        code = body.get("errorcode", body.get("errcode"))
        if code == ERRORCODE_NO_DATA:
            return {"tables": [], "dataVol": 0}
        if code:
            # An expired token mid-run: refresh once and retry.
            if _retry and code in (-1010, -1011, -1012, 401):
                with self._lock:
                    self._access = None
                    self._refresh()
                return self.post(endpoint, payload, _retry=False)
            raise IFindError(code, body.get("errmsg", ""), endpoint)

        self.data_vol += body.get("dataVol") or 0
        return body

    def _post_batched(self, endpoint: str, codes, payload_fn,
                      workers: int = DEFAULT_WORKERS,
                      chunk_size: int | None = None) -> list:
        """Split `codes` into chunks, POST concurrently, concatenate `tables`."""
        codes = list(codes)
        if not codes:
            return []
        # Read the module global at CALL time, not def time, so the batch size
        # stays tunable (and testable) after import.
        chunk_size = chunk_size or MAX_CODES_PER_REQUEST
        chunks = [codes[i:i + chunk_size] for i in range(0, len(codes), chunk_size)]
        if len(chunks) == 1:
            return self.post(endpoint, payload_fn(chunks[0])).get("tables") or []

        tables: list = []
        with ThreadPoolExecutor(max_workers=min(workers, len(chunks))) as ex:
            for body in ex.map(lambda c: self.post(endpoint, payload_fn(c)), chunks):
                tables.extend(body.get("tables") or [])
        return tables

    # -- data endpoints --------------------------------------------------

    def history_quotation(self, codes, indicators: str, beg: str, end: str,
                          cps: str | None = None, fill: str = "Original") -> list:
        """Daily bars. `cps=None`/'1' → 不复权 (raw), '2' → 前复权.

        Raw is what pricedb stores; adjustment lives in `adj_factors`.
        """
        functionpara = {"Fill": fill}
        if cps:
            functionpara["CPS"] = str(cps)
        return self._post_batched(
            "cmd_history_quotation", codes,
            lambda chunk: {"codes": ",".join(chunk), "indicators": indicators,
                           "startdate": beg, "enddate": end,
                           "functionpara": functionpara})

    def real_time(self, codes, indicators: str) -> list:
        """Real-time quotes. After the close these carry the settled bar."""
        return self._post_batched(
            "real_time_quotation", codes,
            lambda chunk: {"codes": ",".join(chunk), "indicators": indicators})

    def basic_data(self, codes, indipara: list) -> list:
        """Point-in-time indicators. `indipara` = [{"indicator":..., "indiparams":[...]}].

        A single bad indicator fails the WHOLE request with -4210, so keep
        indicator sets small and verified.
        """
        return self._post_batched(
            "basic_data_service", codes,
            lambda chunk: {"codes": ",".join(chunk), "indipara": indipara})

    def date_sequence(self, codes, indipara: list, beg: str, end: str,
                      fill: str = "Original") -> list:
        """Indicator time series. Takes `indipara`, NOT `indicators`."""
        return self._post_batched(
            "date_sequence", codes,
            lambda chunk: {"codes": ",".join(chunk), "indipara": indipara,
                           "startdate": beg, "enddate": end,
                           "functionpara": {"Fill": fill}})

    def iwencai(self, query: str, domain: str = "stock") -> dict:
        """Natural-language screen (智能选股).

        Returns the first table's column→values dict, or {} when nothing matched.

        Caveats, all observed 2026-08-25: `searchtype` is ignored (every value
        returns identical stock-level rows); column names embed the query date
        (`涨跌幅:前复权[20260825]`); results include suspended names and
        debut-day outliers, so filter on `上市交易日天数` before using.
        """
        body = self.post("smart_stock_picking",
                         {"searchstring": query, "searchtype": domain})
        tables = body.get("tables") or []
        return (tables[0].get("table") or {}) if tables else {}


# ---------------------------------------------------------------------------
# Module-level convenience
# ---------------------------------------------------------------------------

_CLIENT: IFindClient | None = None
_CLIENT_LOCK = threading.Lock()


def get_client() -> IFindClient:
    """Process-wide singleton, so the token is fetched at most once per run."""
    global _CLIENT
    with _CLIENT_LOCK:
        if _CLIENT is None:
            _CLIENT = IFindClient()
        return _CLIENT


def is_available() -> bool:
    """True when a refresh token is configured. Does not hit the network."""
    return get_client().configured


def reset_client():
    """Drop the singleton (tests)."""
    global _CLIENT
    with _CLIENT_LOCK:
        _CLIENT = None


if __name__ == "__main__":
    client = get_client()
    if not client.configured:
        print("IFIND_REFRESH_TOKEN not set", file=sys.stderr)
        sys.exit(1)
    tables = client.history_quotation(
        ["600519.SH"], "open,high,low,close,volume,amount",
        "2026-08-21", "2026-08-25")
    print(json.dumps(tables, ensure_ascii=False, indent=2))
    print(f"dataVol={client.data_vol}", file=sys.stderr)
