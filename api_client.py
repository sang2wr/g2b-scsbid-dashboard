"""나라장터 낙찰정보(용역) API 클라이언트"""
from __future__ import annotations
import requests
import pandas as pd
from datetime import datetime, timedelta

BASE_URL = "http://apis.data.go.kr/1230000/as/ScsbidInfoService/getScsbidListSttusServcPPSSrch"

# 응답 필드 → 한글 컬럼명 매핑 (실제 API 응답 기준)
FIELD_MAP = {
    "bidNtceNo":     "공고번호",
    "bidNtceOrd":    "공고차수",
    "bidNtceNm":     "공고명",
    "dminsttNm":     "수요기관",
    "prtcptCnum":    "참가업체수",
    "bidwinnrNm":    "낙찰자",
    "bidwinnrBizno": "낙찰자사업자번호",
    "bidwinnrCeoNm": "낙찰자대표자",
    "bidwinnrAdrs":  "낙찰자주소",
    "bidwinnrTelNo": "낙찰자연락처",
    "sucsfbidAmt":   "낙찰금액",
    "sucsfbidRate":  "낙찰율",
    "rlOpengDt":     "개찰일시",
    "rgstDt":        "등록일시",
    "fnlSucsfDate":  "최종낙찰일자",
}


def fetch_scsbid(
    api_key: str,
    keywords: list[str],
    min_amount: int = 0,
    days: int = 7,
    exclude_words: list[str] | None = None,
) -> tuple[pd.DataFrame, str | None]:
    """
    나라장터 용역 낙찰정보를 키워드별로 조회 후 필터링한 DataFrame 반환.
    keywords : OR 검색 — 각 키워드마다 API 호출 후 합산 (비어있으면 기간 내 전체 조회)
    반환: (DataFrame, 에러메시지|None)
    """
    end_dt   = datetime.now()
    start_dt = end_dt - timedelta(days=days)
    bgnDt    = start_dt.strftime("%Y%m%d%H%M")
    endDt    = end_dt.strftime("%Y%m%d%H%M")

    all_rows: list[dict] = []
    error_msg: str | None = None
    search_terms = keywords if keywords else [None]

    for kw in search_terms:
        page = 1
        while True:
            params = {
                "ServiceKey": api_key,
                "type":       "json",
                "numOfRows":  "100",
                "pageNo":     str(page),
                "inqryDiv":   "1",
                "inqryBgnDt": bgnDt,
                "inqryEndDt": endDt,
            }
            if kw:
                params["bidNtceNm"] = kw
            try:
                resp = requests.get(BASE_URL, params=params, timeout=15)
                resp.raise_for_status()
                data = resp.json()
                header = data.get("response", {}).get("header", {})
                result_code = str(header.get("resultCode", "00"))
                if result_code not in ("00", "0"):
                    error_msg = f"API 오류 [{result_code}]: {header.get('resultMsg', '알 수 없는 오류')}"
                    break
                body = data.get("response", {}).get("body", {})
                items = body.get("items") or []
                if isinstance(items, dict):
                    items = [items]
                if not items:
                    break
                all_rows.extend(items)
                total = int(body.get("totalCount", 0))
                if page * 100 >= total:
                    break
                page += 1
            except requests.exceptions.Timeout:
                error_msg = f"API 응답 시간 초과 (키워드={kw}, 페이지={page})"
                break
            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP 오류 {e.response.status_code} (키워드={kw}, 페이지={page})"
                break
            except Exception as e:
                error_msg = f"API 오류 키워드={kw} 페이지={page}: {type(e).__name__}: {e}"
                break
        if error_msg:
            break

    if not all_rows:
        return pd.DataFrame(), error_msg

    df = pd.DataFrame(all_rows)
    df = df.rename(columns={k: v for k, v in FIELD_MAP.items() if k in df.columns})

    dedup_cols = [c for c in ("공고번호", "공고차수") if c in df.columns]
    if dedup_cols:
        df = df.drop_duplicates(subset=dedup_cols)

    if "낙찰금액" in df.columns:
        df["낙찰금액"] = pd.to_numeric(df["낙찰금액"], errors="coerce").fillna(0).astype(int)
        if min_amount > 0:
            df = df[df["낙찰금액"] >= min_amount]

    if "낙찰율" in df.columns:
        df["낙찰율"] = pd.to_numeric(df["낙찰율"], errors="coerce")

    if "참가업체수" in df.columns:
        df["참가업체수"] = pd.to_numeric(df["참가업체수"], errors="coerce").fillna(0).astype(int)

    if exclude_words and "공고명" in df.columns:
        pattern = "|".join(exclude_words)
        df = df[~df["공고명"].str.contains(pattern, na=False)]

    if "개찰일시" in df.columns:
        df["개찰일시"] = pd.to_datetime(df["개찰일시"], errors="coerce")
        df = df.sort_values("개찰일시", ascending=False)

    return df.reset_index(drop=True), error_msg
