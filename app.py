"""나라장터 낙찰정보(용역) 대시보드"""
import streamlit as st
import pandas as pd
from datetime import datetime
import os

from api_client import fetch_scsbid


@st.cache_data
def load_keyword_presets():
    """search.xlsx 모든 컬럼을 (컬럼명, 키워드목록) 튜플 리스트로 반환"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search.xlsx")
    try:
        df = pd.read_excel(path)
        result = []
        for col in df.columns:
            vals = df[col].dropna().astype(str).str.strip().tolist()
            if vals:
                result.append((str(col), vals))
        return result
    except Exception:
        return []


def _load_env_key() -> str:
    try:
        return st.secrets.get("G2B_API_KEY", "") or ""
    except Exception:
        pass
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    if os.path.exists(env_path):
        for line in open(env_path, encoding="utf-8"):
            line = line.strip()
            if line.startswith("G2B_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""


DEFAULT_API_KEY = _load_env_key()

st.set_page_config(
    page_title="나라장터 낙찰정보 대시보드",
    page_icon="🏆",
    layout="wide",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
.metric-card {
  background:#f0f4ff; border-left:4px solid #1a56db;
  border-radius:8px; padding:14px 18px; margin-bottom:0;
}
.metric-title { font-size:13px; color:#6b7280; margin:0; }
.metric-value { font-size:28px; font-weight:700; color:#1a56db; margin:4px 0 0; }
.amount-card  { border-left-color:#065f46 !important; }
.rate-card    { border-left-color:#b45309 !important; }

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin-bottom: 16px;
}

.search-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 20px 24px;
  margin-bottom: 24px;
}

@media (max-width: 768px) {
  .metric-title { font-size: 12px; }
  .metric-value { font-size: 22px; }

  .stTabs [data-baseweb="tab"] {
    font-size: 13px !important;
    padding: 8px 8px !important;
  }

  .stButton > button {
    min-height: 48px !important;
    font-size: 16px !important;
  }

  .stTextInput > div > div > input,
  .stTextArea textarea,
  .stSelectbox > div > div {
    font-size: 16px !important;
  }

  .stDataFrame { overflow-x: auto; }
}
</style>
""", unsafe_allow_html=True)


# ── 헬퍼 함수 ────────────────────────────────────────────────────
def _amt_str(amt) -> str:
    try:
        v = int(amt or 0)
        return f"{v/100_000_000:.1f}억" if v >= 100_000_000 else f"{v//10_000:,}만"
    except Exception:
        return "-"


def show_table(data: pd.DataFrame, tab_key: str = "all"):
    df = data.copy()
    df["낙찰금액_표시"] = df["낙찰금액"].apply(_amt_str)
    df["개찰일"] = df["개찰일시"].astype(str).str[:10]

    q = st.text_input(
        "결과 내 검색",
        placeholder="공고명 · 낙찰자 · 수요기관으로 필터...",
        key=f"q_{tab_key}",
        label_visibility="collapsed",
    )
    fc1, fc2 = st.columns([3, 1])
    with fc1:
        sort_opt = st.selectbox(
            "정렬",
            ["개찰일 최신순", "개찰일 오래된순", "낙찰금액 높은순", "낙찰금액 낮은순", "낙찰율 높은순", "낙찰율 낮은순"],
            key=f"sort_{tab_key}",
            label_visibility="collapsed",
        )
    with fc2:
        st.caption(f"**{len(df):,}건**")

    if q:
        mask = (
            df["공고명"].str.contains(q, case=False, na=False) |
            df["낙찰자"].str.contains(q, case=False, na=False) |
            df["수요기관"].str.contains(q, case=False, na=False)
        )
        df = df[mask]
        st.caption(f"'{q}' 필터 결과: {len(df):,}건")

    sort_map = {
        "개찰일 최신순":   ("개찰일시", False),
        "개찰일 오래된순": ("개찰일시", True),
        "낙찰금액 높은순": ("낙찰금액", False),
        "낙찰금액 낮은순": ("낙찰금액", True),
        "낙찰율 높은순":   ("낙찰율",   False),
        "낙찰율 낮은순":   ("낙찰율",   True),
    }
    sort_col, sort_asc = sort_map[sort_opt]
    if sort_col in df.columns:
        df = df.sort_values(sort_col, ascending=sort_asc, na_position="last")

    show_cols = [c for c in [
        "개찰일", "공고번호", "공고명", "수요기관", "낙찰자",
        "낙찰금액_표시", "낙찰율", "참가업체수", "낙찰자연락처",
    ] if c in df.columns]

    col_cfg = {
        "개찰일":        st.column_config.TextColumn("개찰일",   width=90),
        "공고번호":      st.column_config.TextColumn("공고번호", width=140),
        "공고명":        st.column_config.TextColumn("공고명",   width="large"),
        "수요기관":      st.column_config.TextColumn("수요기관", width=150),
        "낙찰자":        st.column_config.TextColumn("낙찰자",   width=150),
        "낙찰금액_표시": st.column_config.TextColumn("낙찰금액", width=90),
        "낙찰율":        st.column_config.NumberColumn("낙찰율", width=80, format="%.2f%%"),
        "참가업체수":    st.column_config.NumberColumn("참가업체", width=70),
        "낙찰자연락처":  st.column_config.TextColumn("연락처",   width=120),
    }

    row_h = 35
    tbl_h = min(max(400, 38 + len(df) * row_h), 1400)

    st.dataframe(df[show_cols], column_config=col_cfg, hide_index=True,
                 use_container_width=True, height=tbl_h)

    csv = data.to_csv(index=False, encoding="utf-8-sig")
    st.download_button(
        "⬇️ CSV로 저장",
        data=csv,
        file_name=f"나라장터_낙찰정보_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
        key=f"csv_{tab_key}",
    )


def show_winner_rank(data: pd.DataFrame):
    if "낙찰자" not in data.columns:
        return
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("낙찰 건수 상위 낙찰자 (Top 15)")
        st.bar_chart(data["낙찰자"].value_counts().head(15))

    with col_b:
        st.subheader("낙찰 금액 합계 상위 낙찰자 (Top 15)")
        top_amt = data.groupby("낙찰자")["낙찰금액"].sum().sort_values(ascending=False).head(15)
        st.bar_chart(top_amt)

    st.subheader("낙찰자별 상세")
    summary = (
        data.groupby("낙찰자")
        .agg(낙찰건수=("공고번호", "count"), 총낙찰금액=("낙찰금액", "sum"), 평균낙찰율=("낙찰율", "mean"))
        .sort_values("낙찰건수", ascending=False)
        .reset_index()
    )
    summary["총낙찰금액_표시"] = summary["총낙찰금액"].apply(_amt_str)
    st.dataframe(
        summary[["낙찰자", "낙찰건수", "총낙찰금액_표시", "평균낙찰율"]],
        column_config={
            "낙찰자":         st.column_config.TextColumn("낙찰자", width="large"),
            "낙찰건수":       st.column_config.NumberColumn("낙찰건수", width=90),
            "총낙찰금액_표시": st.column_config.TextColumn("총낙찰금액", width=100),
            "평균낙찰율":     st.column_config.NumberColumn("평균낙찰율", format="%.2f%%", width=100),
        },
        hide_index=True, use_container_width=True, height=400,
    )


def show_stats(data: pd.DataFrame):
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("수요기관별 낙찰 건수 (상위 10)")
        if "수요기관" in data.columns:
            st.bar_chart(data["수요기관"].value_counts().head(10))

    with col_b:
        st.subheader("낙찰금액 구간별 분포")
        if "낙찰금액" in data.columns:
            bins = pd.cut(
                data["낙찰금액"],
                bins=[0, 5e7, 1e8, 3e8, 5e8, float("inf")],
                labels=["5천만↓", "5천~1억", "1~3억", "3~5억", "5억↑"],
            )
            st.bar_chart(bins.value_counts().sort_index())

    if "낙찰율" in data.columns:
        st.subheader("낙찰율 분포")
        rate_bins = pd.cut(
            data["낙찰율"],
            bins=[0, 80, 85, 88, 90, 95, 100],
            labels=["~80%", "80~85%", "85~88%", "88~90%", "90~95%", "95~100%"],
        )
        st.bar_chart(rate_bins.value_counts().sort_index())

    if "개찰일시" in data.columns:
        st.subheader("일자별 낙찰 건수")
        daily = (
            data.assign(날짜=data["개찰일시"].dt.date)
            .groupby("날짜").size().rename("건수")
        )
        st.bar_chart(daily)


# ── 메인 ─────────────────────────────────────────────────────────
st.title("상상우리 나라장터 낙찰정보 조회")
st.caption("용역 부문 낙찰정보(개찰완료 건) 조회 — 낙찰자 · 낙찰금액 · 낙찰율을 확인할 수 있습니다.")

# ── API 키: 사이드바에 숨김 ───────────────────────────────────────
with st.sidebar:
    st.subheader("🔑 API 키 설정")
    api_key = st.text_input(
        "공공데이터포털 API 키",
        value=DEFAULT_API_KEY,
        type="password",
        placeholder="발급받은 API 키 입력",
        help="data.go.kr → 나라장터 낙찰정보서비스 활용신청 후 발급한 Decoding 키",
    )

# ── 조회 폼 ──────────────────────────────────────────────────────
with st.form("search_form"):
    st.subheader("🔍 조회 조건")

    preset_groups = load_keyword_presets()

    if preset_groups:
        st.markdown("**🔖 우선순위별 키워드 선택** (OR 검색 — 선택한 키워드 중 하나라도 포함된 공고 조회)")
        grp_cols = st.columns(len(preset_groups))
        sel_all = []
        for i, (grp_name, options) in enumerate(preset_groups):
            with grp_cols[i]:
                sel = st.multiselect(
                    grp_name,
                    options=options,
                    default=[],
                    placeholder=f"{grp_name} 선택...",
                    key=f"ms_grp_{i}",
                )
                sel_all.extend(sel)
    else:
        sel_all = []

    kw_input = st.text_input(
        "추가 키워드 (쉼표로 구분, OR 검색)",
        value="",
        placeholder="위 목록에 없는 키워드 직접 입력 — 예) 박람회, 세미나",
    )

    c1, c2 = st.columns(2)
    with c1:
        min_amount_man = st.number_input(
            "최소 낙찰금액 (만원, 0=전체)",
            value=0, min_value=0, step=500,
        )
    with c2:
        days = st.number_input(
            "개찰일 기준 조회 기간 (일)",
            value=7, min_value=1, max_value=60, step=1,
        )

    excl_input = st.text_input(
        "제외 키워드 (쉼표로 구분)",
        value="",
        placeholder="예) 시담, 재공고",
    )

    submitted = st.form_submit_button("🔄 낙찰정보 조회", use_container_width=True, type="primary")

# ── 조회 처리 ─────────────────────────────────────────────────────
if submitted:
    preset_kws = sel_all
    custom_kws = [k.strip() for k in kw_input.split(",") if k.strip()]
    seen = set()
    keywords = []
    for kw in preset_kws + custom_kws:
        if kw not in seen:
            seen.add(kw)
            keywords.append(kw)
    exclude_words = [e.strip() for e in excl_input.split(",") if e.strip()]
    min_amount = min_amount_man * 10_000

    if not api_key:
        st.error("🔑 API 키를 입력해주세요. 왼쪽 사이드바(☰)의 'API 키 설정'에 입력하세요.")
        st.stop()

    with st.spinner("나라장터에서 낙찰정보를 가져오는 중..."):
        df, err = fetch_scsbid(
            api_key=api_key,
            keywords=keywords,
            min_amount=min_amount,
            days=days,
            exclude_words=exclude_words,
        )

    st.session_state.df           = df
    st.session_state.fetch_error  = err
    st.session_state.last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.search_keywords = keywords

# ── 결과 표시 ─────────────────────────────────────────────────────
if "df" not in st.session_state:
    st.info("⬆️ 조회 조건을 입력하고 **낙찰정보 조회** 버튼을 눌러주세요.")
    st.stop()

if "last_updated" in st.session_state:
    st.caption(f"조회 시각: {st.session_state.last_updated}")

fetch_error = st.session_state.get("fetch_error")
if fetch_error:
    st.error(f"낙찰정보 조회 오류: {fetch_error}")
    st.info("""**API 오류가 발생했다면 활용신청을 확인하세요.**
1. [공공데이터포털](https://www.data.go.kr) 로그인
2. **"조달청 나라장터 낙찰정보서비스"** 검색 → 활용신청
3. 입찰공고 API와 **별도 신청** 필요 (같은 키 사용)
4. 승인 후 마이페이지 → 개발계정 → `Decoding 키` 확인""")

df: pd.DataFrame = st.session_state.df

if df.empty:
    if not fetch_error:
        st.warning("조건에 맞는 낙찰정보가 없습니다. 키워드나 기간을 조정해보세요.")
    st.stop()

search_kws = st.session_state.get("search_keywords", [])
if search_kws:
    st.caption(f"검색 키워드: {', '.join(search_kws)}")

total        = len(df)
total_amount = int(df["낙찰금액"].sum()) if "낙찰금액" in df.columns else 0
avg_rate     = df["낙찰율"].mean() if "낙찰율" in df.columns else None
avg_cnum     = df["참가업체수"].mean() if "참가업체수" in df.columns else None

st.markdown(f"""
<div class="metrics-grid">
  <div class="metric-card">
    <p class="metric-title">전체 낙찰 건수</p>
    <p class="metric-value">{total}건</p>
  </div>
  <div class="metric-card amount-card" style="color:#065f46;">
    <p class="metric-title">총 낙찰금액</p>
    <p class="metric-value" style="color:#065f46;">{total_amount/100_000_000:.1f}억</p>
  </div>
  <div class="metric-card rate-card" style="color:#b45309;">
    <p class="metric-title">평균 낙찰율</p>
    <p class="metric-value" style="color:#b45309;">{f"{avg_rate:.1f}%" if avg_rate is not None and pd.notnull(avg_rate) else "-"}</p>
  </div>
  <div class="metric-card">
    <p class="metric-title">평균 참가업체수</p>
    <p class="metric-value">{f"{avg_cnum:.1f}개" if avg_cnum is not None and pd.notnull(avg_cnum) else "-"}</p>
  </div>
</div>
""", unsafe_allow_html=True)

st.divider()

tab1, tab2, tab3 = st.tabs(["📋 전체 목록", "🏆 낙찰자 순위", "📊 통계"])

with tab1:
    show_table(df, tab_key="all")

with tab2:
    show_winner_rank(df)

with tab3:
    show_stats(df)
