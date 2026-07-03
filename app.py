# -*- coding: utf-8 -*-
"""키워드 검색량 트렌드 — 네이버 공식 API(pluszero 공식 재현) + LINKPORT 디자인 시스템."""
import datetime as dt
import re

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from naver_volume import estimate_daily_volume, DATALAB_START

st.set_page_config(page_title="키워드 검색량 트렌드", page_icon="📈", layout="wide")

# ─────────────────── LINKPORT 디자인 시스템 토큰 ───────────────────
BG = "#FAF9F6"        # 크림 배경
SURFACE = "#FFFFFF"   # 흰 카드
INK = "#2D2B28"       # 제목
BODY = "#3D3B38"      # 본문
MUTED = "#8C8680"     # 라벨/캡션
BORDER = "#E8E4DE"
GRID = "#E8E4DE"
ACCENT = "#D97757"    # 테라코타 (강조 딱 한 곳)
# 다중 키워드용 브랜드 팔레트
PALETTE = ["#D97757", "#6B9B7A", "#7B8DBF", "#B8956A", "#9B7A8D"]

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap');

html, body, [class*="css"], [data-testid="stMarkdown"], [data-testid="stMetric"],
input, button, select, textarea, h1,h2,h3,h4,h5,h6, p, div, label,
span:not([data-testid="stIconMaterial"]) {
    font-family: 'Noto Sans KR', sans-serif !important;
}
.stApp, [data-testid="stAppViewContainer"] { background-color: #FAF9F6 !important; }
[data-testid="stMainBlockContainer"] { padding-top: 3rem; max-width: 1180px; }

/* 다크 사이드바 */
section[data-testid="stSidebar"] > div:first-child { background: #2D2B28 !important; }
section[data-testid="stSidebar"] * { color: #E8E4DE !important; }
section[data-testid="stSidebar"] textarea {
    background: #3D3B38 !important; color: #E8E4DE !important;
    border: 1px solid #4A4745 !important; border-radius: 8px !important;
}
section[data-testid="stSidebar"] hr { border-color: #4A4745 !important; }
.brand { letter-spacing:.28em; font-weight:700; font-size:1.25rem; color:#E8E4DE; margin:.2rem 0 0; }
.brand-sub { letter-spacing:.2em; font-size:.62rem; color:#8C8680;
             margin-bottom:1.2rem; padding-bottom:1rem; border-bottom:1px solid #4A4745; }

/* 폰트/제목 */
h1 { color:#2D2B28 !important; font-weight:700 !important; font-size:1.8rem !important; letter-spacing:-.01em; }
.subtle { color:#8C8680; font-size:.9rem; font-weight:400; }

/* 섹션 타이틀 (테라코타 밑줄) */
.section-title {
    display:inline-block; color:#2D2B28; font-size:1.05rem; font-weight:600;
    margin:28px 0 16px; padding-bottom:8px; border-bottom:2px solid #D97757;
}

/* 메트릭 카드 */
[data-testid="stMetric"] {
    background:#FFFFFF; border:1px solid #E8E4DE; border-radius:12px;
    padding:18px 22px; box-shadow:0 1px 3px rgba(45,43,40,.06); transition:box-shadow .2s;
}
[data-testid="stMetric"]:hover { box-shadow:0 4px 12px rgba(45,43,40,.1); }
[data-testid="stMetricLabel"] { font-size:.8rem; color:#8C8680 !important; font-weight:500; }
[data-testid="stMetricValue"] { color:#2D2B28 !important; font-weight:700;
    font-variant-numeric:tabular-nums; }

/* primary 버튼 = 테라코타 */
.stButton > button[kind="primary"] {
    background:#D97757 !important; border-color:#D97757 !important; color:#fff !important;
    border-radius:8px !important; font-weight:600 !important;
}
.stButton > button[kind="primary"]:hover { background:#C4694D !important; border-color:#C4694D !important; }

/* 차트 컨테이너 */
/* 달력 팝업의 영어 '빠른 선택'(Past Week 등) 블록 숨김 — 우리 한글 프리셋으로 대체 */
[data-baseweb="calendar"] > div:has([data-baseweb="form-control-container"]) { display:none !important; }

.stPlotlyChart { background:#FFFFFF; border:1px solid #E8E4DE; border-radius:12px; padding:8px; }
[data-testid="stExpander"] { border:1px solid #E8E4DE; border-radius:10px; background:#FFFFFF; }
hr { border-color:#E8E4DE !important; }
</style>
""", unsafe_allow_html=True)


# ─── 달력 월·요일 한글화 (baseweb 기본 영어 → 한글). 프리셋 블록은 CSS로 숨김 ───
components.html("""
<script>
const M={January:'1월',February:'2월',March:'3월',April:'4월',May:'5월',June:'6월',
July:'7월',August:'8월',September:'9월',October:'10월',November:'11월',December:'12월'};
const D={Su:'일',Mo:'월',Tu:'화',We:'수',Th:'목',Fr:'금',Sa:'토'};
function tr(){
  const doc=window.parent.document;
  doc.querySelectorAll('[data-baseweb="calendar"], [data-baseweb="popover"], [role="listbox"]').forEach(c=>{
    const w=doc.createTreeWalker(c, NodeFilter.SHOW_TEXT); let n;
    while(n=w.nextNode()){ const t=n.nodeValue.trim();
      if(M[t]) n.nodeValue=M[t]; else if(D[t]) n.nodeValue=D[t]; }
  });
}
new MutationObserver(tr).observe(window.parent.document.body,{childList:true,subtree:true});
setInterval(tr,150);
tr();
</script>
""", height=0)


def load_creds():
    s = st.secrets
    return {
        "ad_api_key": s["NAVER_AD_API_KEY"],
        "ad_secret_key": s["NAVER_AD_SECRET_KEY"],
        "ad_customer_id": s["NAVER_AD_CUSTOMER_ID"],
        "client_id": s["NAVER_CLIENT_ID"],
        "client_secret": s["NAVER_CLIENT_SECRET"],
    }


@st.cache_data(ttl=60 * 60 * 6, show_spinner=False)
def fetch(keyword, day_key):
    return estimate_daily_volume(keyword, load_creds())


def aggregate(df, unit):
    d = df.copy()
    d["date"] = pd.to_datetime(d["date"])
    if unit == "일간":
        d["bucket"] = d["date"]
    elif unit == "주간":
        d["bucket"] = d["date"].dt.to_period("W").dt.start_time
    elif unit == "월간":
        d["bucket"] = d["date"].dt.to_period("M").dt.start_time
    else:
        d["bucket"] = d["date"].dt.to_period("Y").dt.start_time
    g = d.groupby(["keyword", "bucket"], as_index=False)["volume"].sum()
    return g.rename(columns={"bucket": "date"})


# ─────────── 비밀번호 게이트 (secrets에 APP_PASSWORD 있으면 잠금, 없으면 공개) ───────────
def _check_password():
    try:
        pw = st.secrets.get("APP_PASSWORD", "")
    except Exception:
        pw = ""
    if not pw:
        return True
    if st.session_state.get("auth_ok"):
        return True
    st.markdown("## 🔒 접근 비밀번호")
    entered = st.text_input("비밀번호", type="password", label_visibility="collapsed")
    if entered:
        if entered == pw:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    return False


if not _check_password():
    st.stop()


# ─────────────────────────────── 사이드바 ───────────────────────────────
with st.sidebar:
    st.markdown('<div class="brand">LINKPORT</div>', unsafe_allow_html=True)
    st.markdown('<div class="brand-sub">KEYWORD SEARCH TREND</div>', unsafe_allow_html=True)
    kw_text = st.text_area("키워드 (쉼표 또는 줄바꿈으로 구분, 최대 5개)", value="마카", height=120)
    go_btn = st.button("조회하기", type="primary", use_container_width=True)
    st.markdown('<div class="subtle" style="margin-top:1.2rem;">데이터 · 네이버 검색광고 × 데이터랩<br>'
                f'{dt.date.today():%Y년 %m월 %d일} 기준</div>', unsafe_allow_html=True)

# ─────────────────────────────── 조회 처리 ───────────────────────────────
if go_btn:
    keywords = [k.strip() for k in re.split(r"[,\n，、]+", kw_text) if k.strip()][:5]
    if not keywords:
        st.warning("키워드를 입력해주세요.")
    else:
        day_key = dt.date.today().isoformat()
        results, frames = [], []
        prog = st.progress(0.0, text="네이버 API 조회 중...")
        for i, kw in enumerate(keywords, 1):
            try:
                res = fetch(kw, day_key)
                results.append(res)
                df = pd.DataFrame(res["daily"]); df["keyword"] = kw
                frames.append(df)
            except Exception as e:
                st.error(f"[{kw}] 조회 실패: {e}")
            prog.progress(i / len(keywords), text=f"{kw} 완료")
        prog.empty()
        if frames:
            st.session_state["results"] = results
            st.session_state["data"] = pd.concat(frames, ignore_index=True)

# ─────────────────────────────── 본문 ───────────────────────────────
today = dt.date.today()
st.markdown(f"# 키워드 검색량 트렌드　<span class='subtle'>{today:%Y년 %m월 %d일 (%a)}</span>",
            unsafe_allow_html=True)

if "data" not in st.session_state:
    st.info("왼쪽에서 키워드를 입력하고 **조회하기**를 누르세요.")
    st.stop()

results = st.session_state["results"]
all_df = st.session_state["data"].copy()
all_df["date"] = pd.to_datetime(all_df["date"]).dt.date

# 월검색량 요약
st.markdown('<div class="section-title">Naver 최근 30일 검색량</div>', unsafe_allow_html=True)
cols = st.columns(max(len(results), 1))
for c, r in zip(cols, results):
    c.metric(r["keyword"], f"{r['total']:,}", help=f"PC {r['pc']:,} · MO {r['mo']:,}")

# 그래프 컨트롤
st.markdown('<div class="section-title">트렌드 그래프</div>', unsafe_allow_html=True)
yesterday = today - dt.timedelta(days=1)
PRESETS = {"직접 선택": None, "최근 3일": 3, "최근 1주일": 7, "최근 1개월": 30,
           "최근 3개월": 91, "최근 6개월": 182, "최근 1년": 365, "최근 2년": 730, "전체": "all"}
c1, c2, c3 = st.columns([2, 3, 3])
with c1:
    preset = st.selectbox("빠른 기간", list(PRESETS.keys()), index=0)
with c2:
    default_start = dt.date(today.year - 2, 1, 1)
    date_range = st.date_input("기간 (직접 선택)", value=(default_start, yesterday),
                               min_value=dt.date.fromisoformat(DATALAB_START),
                               max_value=yesterday)
with c3:
    unit = st.radio("집계 단위", ["일간", "주간", "월간", "연간"], index=0, horizontal=True)

p = PRESETS[preset]
if p is None:   # 직접 선택 → 달력 범위 사용
    if isinstance(date_range, (list, tuple)) and len(date_range) == 2:
        start_d, end_d = date_range
    else:
        start_d, end_d = default_start, yesterday
elif p == "all":
    start_d, end_d = dt.date.fromisoformat(DATALAB_START), yesterday
else:
    start_d, end_d = yesterday - dt.timedelta(days=p - 1), yesterday

view = all_df[(all_df["date"] >= start_d) & (all_df["date"] <= end_d)].copy()
view["date"] = view["date"].astype(str)
agg = aggregate(view, unit)

# ─────────────── Plotly 차트 (디자인 시스템: 직선·채움없음·한글·툴바없음) ───────────────
fig = go.Figure()
for idx, (kw, sub) in enumerate(agg.groupby("keyword")):
    color = PALETTE[idx % len(PALETTE)]
    fig.add_trace(go.Scatter(
        x=sub["date"], y=sub["volume"], mode="lines", name=kw,
        line=dict(color=color, width=2.4),
        hovertemplate="<b>" + kw + "</b>　%{y:,}<extra></extra>",
    ))
fig.update_layout(
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="#FFFFFF",
    font=dict(color=BODY, family="Noto Sans KR"),
    margin=dict(l=20, r=20, t=30, b=20), height=440,
    legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(color=INK)),
    xaxis=dict(
        gridcolor=GRID, showline=False, title=None,
        hoverformat="%Y년 %m월 %d일",
        tickformatstops=[
            dict(dtickrange=[None, 604800000], value="%m월 %d일"),      # ~1주
            dict(dtickrange=[604800000, "M1"], value="%m월 %d일"),      # ~1개월
            dict(dtickrange=["M1", "M12"], value="%Y년 %m월"),          # ~1년
            dict(dtickrange=["M12", None], value="%Y년"),               # 1년+
        ],
    ),
    yaxis=dict(gridcolor=GRID, zeroline=False, title=None, tickformat=","),
    hoverlabel=dict(bgcolor="rgba(45,43,40,.95)", font_color="#FAF9F6",
                    bordercolor=ACCENT, font_family="Noto Sans KR"),
    hovermode="x unified",
)
st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

# 표 + CSV
with st.expander("데이터 표 / CSV 다운로드"):
    pivot = agg.pivot_table(index="date", columns="keyword", values="volume").reset_index()
    fmt = "%Y" if unit == "연간" else ("%Y-%m" if unit == "월간" else "%Y-%m-%d")
    pivot["date"] = pd.to_datetime(pivot["date"]).dt.strftime(fmt)
    pivot = pivot.rename(columns={"date": "날짜"})
    pivot.columns.name = None
    st.dataframe(pivot, use_container_width=True, hide_index=True)
    st.download_button("CSV 다운로드", pivot.to_csv(index=False).encode("utf-8-sig"),
                       file_name=f"volume_{unit}.csv", mime="text/csv")
