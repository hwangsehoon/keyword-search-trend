# -*- coding: utf-8 -*-
"""네이버 공식 API로 키워드 일별 검색량 추정 (pluszero navertrend 공식 재현).

핵심 함수는 자격증명(creds dict)을 인자로 받아 Streamlit/CLI 어디서든 재사용.
creds = {
    "ad_api_key": ..., "ad_secret_key": ..., "ad_customer_id": ...,
    "client_id": ..., "client_secret": ...,
}
"""
import base64
import datetime as dt
import hashlib
import hmac
import json
import time
import urllib.parse
import urllib.request

SEARCHAD_BASE = "https://api.searchad.naver.com"
DATALAB_START = "2016-01-01"   # 데이터랩 최소 시작일 = pluszero와 동일


# ── 검색광고: 월 PC/MO 검색수 ─────────────────────────────────────────
def _sign(secret, timestamp, method, uri):
    msg = f"{timestamp}.{method}.{uri}"
    sig = hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()
    return base64.b64encode(sig).decode("utf-8")


def _parse_qc(v):
    if isinstance(v, str):
        v = v.replace("<", "").replace(",", "").strip()
        try:
            return int(v)
        except ValueError:
            return 0
    return int(v or 0)


def get_monthly_volume(keyword, creds):
    uri, method = "/keywordstool", "GET"
    ts = str(int(time.time() * 1000))
    headers = {
        "X-Timestamp": ts,
        "X-API-KEY": creds["ad_api_key"],
        "X-Customer": str(creds["ad_customer_id"]),
        "X-Signature": _sign(creds["ad_secret_key"], ts, method, uri),
    }
    hint = keyword.replace(" ", "")
    url = f"{SEARCHAD_BASE}{uri}?hintKeywords={urllib.parse.quote(hint)}&showDetail=1"
    req = urllib.request.Request(url, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=15) as r:
        data = json.loads(r.read().decode("utf-8"))
    rows = data.get("keywordList", [])
    for row in rows:
        if row.get("relKeyword", "").replace(" ", "") == hint:
            return _parse_qc(row.get("monthlyPcQcCnt")), _parse_qc(row.get("monthlyMobileQcCnt"))
    if rows:
        row = rows[0]
        return _parse_qc(row.get("monthlyPcQcCnt")), _parse_qc(row.get("monthlyMobileQcCnt"))
    return 0, 0


# ── 데이터랩: 일별 비율 ───────────────────────────────────────────────
def get_daily_ratio(keyword, start_date, end_date, creds):
    body = json.dumps({
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "date",
        "keywordGroups": [{"groupName": keyword, "keywords": [keyword]}],
    }).encode("utf-8")
    req = urllib.request.Request(
        "https://openapi.naver.com/v1/datalab/search",
        data=body,
        headers={
            "X-Naver-Client-Id": creds["client_id"],
            "X-Naver-Client-Secret": creds["client_secret"],
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        data = json.loads(r.read().decode("utf-8"))
    results = data.get("results", [])
    if not results:
        return {}
    return {p["period"]: p["ratio"] for p in results[0]["data"]}


# ── 합성: 일별 추정 검색량 (pluszero 공식 그대로) ─────────────────────
def _daterange(start, end):
    cur = start
    while cur <= end:
        yield cur
        cur += dt.timedelta(days=1)


def estimate_daily_volume(keyword, creds, start_date=DATALAB_START, end_date=None):
    end = dt.date.fromisoformat(end_date) if end_date else dt.date.today() - dt.timedelta(days=1)
    start = dt.date.fromisoformat(start_date)

    ratio_map = get_daily_ratio(keyword, start.isoformat(), end.isoformat(), creds)
    pc, mo = get_monthly_volume(keyword, creds)
    total = pc + mo

    dates = [d.isoformat() for d in _daterange(start, end)]
    daily = [ratio_map.get(d, 0) for d in dates]

    last30_sum = sum(daily[-30:])
    coeff = (total / last30_sum) if last30_sum > 0 else 0.0

    rows = [{"date": d, "volume": int(round(v * coeff))} for d, v in zip(dates, daily)]
    return {
        "keyword": keyword, "pc": pc, "mo": mo, "total": total,
        "last30_sum": last30_sum, "coefficient": coeff, "daily": rows,
    }
