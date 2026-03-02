#!/usr/bin/env python3
"""
CheeseForTune (芝士财富) API Client

Reverse-engineered from stock.cheesefortune.com frontend.
Provides structured stock data: valuation, financials, scores, events, peers.

Auth: JWT token (expires 2036) + dynamic zstokv1 (MD5 of timestamp + AES-encrypted chunk).

Usage:
    from cheesefortune_client import CheeseFortuneClient
    client = CheeseFortuneClient()
    data = client.get_stock_summary("688102.SH")
    
    # Or CLI:
    python cheesefortune_client.py summary 688102.SH
    python cheesefortune_client.py batch 688102.SH 300684.SZ 600499.SH
    python cheesefortune_client.py pepb 688102.SH
"""

import hashlib
import time
import json
import ssl
import sys
import urllib.request
import base64
import os
from pathlib import Path
from typing import Optional

# Optional: pycryptodome for AES
try:
    from Crypto.Cipher import AES
    from Crypto.Util.Padding import pad
    HAS_CRYPTO = True
except ImportError:
    HAS_CRYPTO = False


class CheeseFortuneClient:
    """API client for stock.cheesefortune.com"""

    BASE_URL = "https://stock.cheesefortune.com"
    AES_KEY = "vGEZCiIXRIImAWSv"
    MIN_REQUEST_INTERVAL = 2.5  # seconds between requests to avoid rate limiting

    def __init__(self, user_token: Optional[str] = None):
        """
        Args:
            user_token: JWT auth token. Falls back to CHEESEFORTUNE_TOKEN env var,
                        then to ~/.cheesefortune_token file.
        """
        self.user_token = user_token or self._load_token()
        self.api_auth_token: Optional[str] = None
        self._last_request_time = 0.0

        # SSL context (their cert has issues)
        self._ssl_ctx = ssl.create_default_context()
        self._ssl_ctx.check_hostname = False
        self._ssl_ctx.verify_mode = ssl.CERT_NONE

        if not HAS_CRYPTO:
            raise ImportError(
                "pycryptodome is required: pip install pycryptodome"
            )

    def _load_token(self) -> str:
        """Load user token from env or file."""
        token = os.environ.get("CHEESEFORTUNE_TOKEN")
        if token:
            return token
        token_file = Path.home() / ".cheesefortune_token"
        if token_file.exists():
            return token_file.read_text().strip()
        raise ValueError(
            "No token found. Set CHEESEFORTUNE_TOKEN env var or create ~/.cheesefortune_token"
        )

    def _ensure_api_token(self):
        """Fetch the apiAuthToken from the server (cached per session)."""
        if self.api_auth_token:
            return
        url = f"{self.BASE_URL}/api/v2/system/apiOuth"
        req = urllib.request.Request(url, headers={
            "Content-Type": "application/json;charset=utf-8"
        })
        with urllib.request.urlopen(req, context=self._ssl_ctx) as resp:
            data = json.loads(resp.read())
        if data.get("code") != "000" or not data.get("datas"):
            raise RuntimeError(f"Failed to get API auth token: {data}")
        self.api_auth_token = data["datas"]

    def _make_headers(self) -> dict:
        """Generate authenticated headers with fresh zstokv1."""
        self._ensure_api_token()
        ts = int(time.time() * 1000)
        # Split token into 8-char chunks
        chunks = [
            self.api_auth_token[i:i+8]
            for i in range(0, len(self.api_auth_token), 8)
        ]
        # AES-ECB encrypt the chunk at index (timestamp % 10)
        cipher = AES.new(self.AES_KEY.encode("latin-1"), AES.MODE_ECB)
        plaintext = chunks[ts % 10].encode("latin-1")
        encrypted = base64.b64encode(
            cipher.encrypt(pad(plaintext, AES.block_size))
        ).decode()
        # zstokv1 = MD5(timestamp + encrypted)
        zstokv1 = hashlib.md5(f"{ts}{encrypted}".encode()).hexdigest()

        return {
            "Content-Type": "application/json;charset=utf-8",
            "token": self.user_token,
            "requestFrom": "wechat",
            "deviceType": "pc",
            "runtimeType": "browser",
            "zstokv1": zstokv1,
            "timeStamp": str(ts),
        }

    def _throttle(self):
        """Rate limit requests."""
        now = time.time()
        elapsed = now - self._last_request_time
        if elapsed < self.MIN_REQUEST_INTERVAL:
            time.sleep(self.MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _request(self, url: str, data: Optional[dict] = None) -> dict:
        """Make an authenticated API request with rate limiting."""
        self._throttle()
        headers = self._make_headers()
        body = json.dumps(data).encode() if data else None
        method = "POST" if data else "GET"
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, context=self._ssl_ctx) as resp:
                result = json.loads(resp.read())
        except urllib.error.HTTPError as e:
            return {"code": str(e.code), "message": str(e), "datas": None}

        if result.get("code") == "-002":
            # Rate limited — wait and retry once
            time.sleep(5)
            self._last_request_time = time.time()
            headers = self._make_headers()
            req = urllib.request.Request(url, data=body, headers=headers, method=method)
            with urllib.request.urlopen(req, context=self._ssl_ctx) as resp:
                result = json.loads(resp.read())

        return result

    # =========================================================================
    # High-level API methods
    # =========================================================================

    def get_base_info(self, code: str) -> Optional[dict]:
        """Stock base info: PE/PB/PS, valuation percentile, industry chain.
        
        Returns dict with keys:
            name, pepb{pe,pb,ps,pcf}, indexGZPer (valuation percentile),
            indexList (industry chain), totalShare
        """
        r = self._request(f"{self.BASE_URL}/api/v3/details/stockBaseInfo?code={code}")
        return r.get("datas") if r.get("code") == "000" else None

    def get_vip_data(self, code: str) -> Optional[dict]:
        """AI scoring and commentary.
        
        Returns dict with keys:
            score1{scoreCompany, scoreTrend, scoreValue},
            comment_new{positive_new[], unpositive_new[]}
        """
        r = self._request(f"{self.BASE_URL}/api/v3/details/vipData", {"code": code})
        return r.get("datas") if r.get("code") == "000" else None

    def get_pepb_history(self, code: str, years: str = "5Y") -> Optional[dict]:
        """PE/PB history (daily data points).
        
        Args:
            years: "3Y", "5Y", "10Y", "50Y" (50Y = since listing)
            
        Returns dict with keys:
            msg (valuation summary HTML), datas[] ({x: date, y: value}),
            newest{pe, pb, ps, pcf, zhgz (percentile)}
        """
        r = self._request(
            f"{self.BASE_URL}/api/v3/details/pepb?code={code}&type=indexGZPer&years={years}"
        )
        return r.get("datas") if r.get("code") == "000" else None

    def get_events(self, code: str, size: int = 5) -> Optional[list]:
        """Upcoming events (earnings dates, lockup expiry, dividends, etc.)
        
        Returns list of event dicts with keys:
            name, content, effectdateMap{beginDate}, tagDescMap[{tag}]
        """
        r = self._request(
            f"{self.BASE_URL}/api/v2/eventReminder/list?code={code}&size={size}&page=stockinfo"
        )
        return r.get("datas") if r.get("code") == "000" else None

    def get_intro(self, code: str) -> Optional[dict]:
        """Company profile: industry, concepts, holders, business description.
        
        Returns dict with keys:
            basic{name, area, holder, briefing, holderTop1Pct, ...},
            industry{industrys[]}, concept{concepts[]}
        """
        r = self._request(f"{self.BASE_URL}/api/v3/details/stockIntro?code={code}")
        return r.get("datas") if r.get("code") == "000" else None

    def get_financials(self, code: str, period: str = "20250930") -> Optional[dict]:
        """Financial report quick view: income statement with YoY growth.
        
        Args:
            period: YYYYMMDD format — use quarter-end dates (0331, 0630, 0930, 1231)
            
        Returns dict with income statement breakdown including chgPct (YoY change).
        """
        r = self._request(
            f"{self.BASE_URL}/api/v3/details/finreportQuick?code={code}&reportPeriod={period}"
        )
        return r.get("datas") if r.get("code") == "000" else None

    def get_industry_compare(self, code: str) -> Optional[dict]:
        """Peer comparison: rank within industry for key metrics.
        
        Returns dict with catalog[] (metrics list) and ranking data.
        """
        r = self._request(
            f"{self.BASE_URL}/api/v3/details/industryCompareDetail?code={code}"
        )
        return r.get("datas") if r.get("code") == "000" else None

    def get_kline(self, code: str, days: int = 5) -> Optional[list]:
        """Intraday/daily kline data.
        
        Returns list of [date, price, volume, amount, time_slot, null].
        """
        r = self._request(
            f"{self.BASE_URL}/api/v2/k/subscribeShare?code={code}&days={days}&isCN=true"
        )
        return r.get("datas") if r.get("code") == "000" else None

    def get_strategy_signals(self, code: str) -> Optional[dict]:
        """Strategy signals and change alerts for a stock."""
        r = self._request(
            f"{self.BASE_URL}/api/v3/stockP/stockStrategysDetail?code={code}"
        )
        return r.get("datas") if r.get("code") == "000" else None

    # =========================================================================
    # Composite methods
    # =========================================================================

    def get_stock_summary(self, code: str) -> dict:
        """Get a comprehensive summary for one stock.
        
        Makes 5 API calls (~12.5s with rate limiting).
        Returns a flat dict with all key data for FA analysis.
        """
        summary = {"code": code, "fetch_time": time.strftime("%Y-%m-%dT%H:%M:%S%z")}

        # 1. Base info (PE/PB, valuation percentile)
        base = self.get_base_info(code)
        if base:
            summary["name"] = base.get("name")
            pepb = base.get("pepb", {})
            summary["pe"] = pepb.get("pe")
            summary["pb"] = pepb.get("pb")
            summary["ps_ttm"] = pepb.get("ps")
            summary["pcf_ttm"] = pepb.get("pcf")
            summary["valuation_percentile"] = base.get("indexGZPer")
            summary["total_shares"] = base.get("totalShare")
            # Industry chain
            industries = base.get("indexList", [])
            summary["industries"] = [
                {"name": idx["name"], "level": idx.get("level")}
                for idx in industries
                if idx.get("capitalOrIndex") == "index_hy"
            ]
            summary["concepts"] = [
                idx["name"] for idx in industries
                if idx.get("capitalOrIndex") == "index_gn"
            ]

        # 2. AI scores + commentary
        vip = self.get_vip_data(code)
        if vip:
            scores = vip.get("score1", {})
            summary["score_company"] = scores.get("scoreCompany")
            summary["score_trend"] = scores.get("scoreTrend")
            summary["score_value"] = scores.get("scoreValue")
            comment = vip.get("comment_new", {})
            summary["highlights"] = [
                {"tag": c["tag"], "text": c["value"]}
                for c in comment.get("positive_new", [])
            ]
            summary["risks"] = [
                {"tag": c["tag"], "text": c["value"]}
                for c in comment.get("unpositive_new", [])
            ]

        # 3. Upcoming events
        events = self.get_events(code)
        if events:
            summary["events"] = []
            for e in events[:5]:
                ev = {
                    "content": e.get("content", ""),
                    "tags": [t["tag"] for t in e.get("tagDescMap", [])],
                }
                dates = e.get("effectdateMap", {})
                if dates:
                    ev["date"] = dates.get("beginDate")
                summary["events"].append(ev)

        # 4. Financials (latest available quarter)
        for period in ["20250930", "20250630", "20251231"]:
            fin = self.get_financials(code, period)
            if fin:
                income = fin.get("income", {}).get("sangji", {})
                if income:
                    summary["report_period"] = period
                    rev = income.get("TOT_OPER_REV", {})
                    summary["revenue"] = rev.get("value")
                    summary["revenue_yoy"] = rev.get("chgPct")
                    profit = income.get("OPER_PROFIT", {})
                    summary["operating_profit"] = profit.get("value")
                    summary["operating_profit_yoy"] = profit.get("chgPct")
                    net = profit.get("child", {}).get("NET_PROFIT_INCL_MIN_INT_INC", {})
                    summary["net_profit"] = net.get("value")
                    summary["net_profit_yoy"] = net.get("chgPct")
                    gross = income.get("GROSS_PROFIT", {})
                    summary["gross_profit"] = gross.get("value")
                    summary["gross_profit_yoy"] = gross.get("chgPct")
                    cost = income.get("LESS_OPER_COST", {})
                    summary["cogs"] = cost.get("value")
                    # Gross margin
                    if rev.get("value") and rev["value"] > 0:
                        summary["gross_margin"] = round(
                            gross.get("value", 0) / rev["value"] * 100, 2
                        )
                break  # Got financials, stop trying periods

        # 5. PE/PB valuation context
        pepb_hist = self.get_pepb_history(code, "5Y")
        if pepb_hist:
            newest = pepb_hist.get("newest", {})
            summary["pe_forward"] = newest.get("peFor")
            # Count data points to understand history depth
            datas = pepb_hist.get("datas", [])
            if datas:
                summary["valuation_history_days"] = len(datas)
                summary["valuation_history_from"] = datas[0].get("x")

        return summary

    def get_batch_summaries(self, codes: list[str]) -> list[dict]:
        """Get summaries for multiple stocks.
        
        Args:
            codes: List of stock codes like ["688102.SH", "300684.SZ"]
            
        Returns list of summary dicts.
        """
        results = []
        for i, code in enumerate(codes):
            print(f"  [{i+1}/{len(codes)}] Fetching {code}...", file=sys.stderr)
            try:
                summary = self.get_stock_summary(code)
                results.append(summary)
            except Exception as e:
                results.append({"code": code, "error": str(e)})
        return results


# =============================================================================
# Utility: normalize stock code to CheeseForTune format
# =============================================================================

def normalize_code(code: str) -> str:
    """Convert stock code to CheeseForTune format (CODE.EXCHANGE).
    
    Examples:
        "688102" -> "688102.SH"
        "300684" -> "300684.SZ"
        "688102.SH" -> "688102.SH" (passthrough)
    """
    if "." in code:
        return code.upper()
    code = code.strip()
    if code.startswith("6"):
        return f"{code}.SH"
    elif code.startswith("0") or code.startswith("3"):
        return f"{code}.SZ"
    else:
        return f"{code}.SH"  # default to Shanghai


# =============================================================================
# CLI
# =============================================================================

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python cheesefortune_client.py summary 688102.SH")
        print("  python cheesefortune_client.py batch 688102.SH 300684.SZ 600499.SH")
        print("  python cheesefortune_client.py base 688102.SH")
        print("  python cheesefortune_client.py vip 688102.SH")
        print("  python cheesefortune_client.py pepb 688102.SH [5Y|10Y]")
        print("  python cheesefortune_client.py events 688102.SH")
        print("  python cheesefortune_client.py financials 688102.SH [20250930]")
        print("  python cheesefortune_client.py intro 688102.SH")
        print("  python cheesefortune_client.py peers 688102.SH")
        sys.exit(1)

    cmd = sys.argv[1]
    code = normalize_code(sys.argv[2])
    client = CheeseFortuneClient()

    if cmd == "summary":
        result = client.get_stock_summary(code)
    elif cmd == "batch":
        codes = [normalize_code(c) for c in sys.argv[2:]]
        result = client.get_batch_summaries(codes)
    elif cmd == "base":
        result = client.get_base_info(code)
    elif cmd == "vip":
        result = client.get_vip_data(code)
    elif cmd == "pepb":
        years = sys.argv[3] if len(sys.argv) > 3 else "5Y"
        result = client.get_pepb_history(code, years)
    elif cmd == "events":
        result = client.get_events(code)
    elif cmd == "financials":
        period = sys.argv[3] if len(sys.argv) > 3 else "20250930"
        result = client.get_financials(code, period)
    elif cmd == "intro":
        result = client.get_intro(code)
    elif cmd == "peers":
        result = client.get_industry_compare(code)
    else:
        print(f"Unknown command: {cmd}", file=sys.stderr)
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
