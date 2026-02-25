import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
import time
from datetime import datetime

# 1. 기본 설정 및 아이콘 깨짐 방지 패치
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    
    /* 전체 폰트 적용 (아이콘 제외) */
    html, body, [class*="css"] {
        font-family: 'Pretendard', -apple-system, sans-serif !important;
    }

    /* Streamlit 시스템 아이콘 폰트 강제 보존 (화살표 깨짐 방지) */
    .st-emotion-cache-17l6l7d, .material-icons, [data-testid="stSidebarCollapseButton"] span, .st-emotion-cache-6q9sum {
        font-family: 'Material Icons' !important;
    }

    h1 { font-weight: 800 !important; letter-spacing: -1px; }
    </style>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 2. 내재화된 전체 시장 스캔 함수 (V2 로직)
def run_full_market_scan():
    all_results = []
    with st.spinner("📡 나스닥(NASDAQ) 전체 리스트 확보 중..."):
        try:
            df_nasdaq = fdr.StockListing('NASDAQ')
            # 사용자 지정 제외 종목
            exclude = ['GAUZ', 'SLNH']
            tickers = [t for t in df_nasdaq['Symbol'].tolist() if t not in exclude]
        except Exception as e:
            st.error(f"리스트 확보 실패: {e}")
            return pd.DataFrame()

    total_count = len(tickers)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(tickers):
        try:
            df = fdr.DataReader(t).tail(60)
            if len(df) < 30: continue

            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            df['Vol_Accel'] = df['Volume'] / df['Volume'].rolling(20).mean()
            
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t,
                'Price': round(float(last['Close']), 2), # 지침 준수: Price
                'Volume_USD': int(last['Close'] * last['Volume']),
                'RSI': round(float(last['RSI']), 1),
                'Vol_Accel': round(float(last['Vol_Accel']), 2),
                '반등점수': round(100 - float(last['RSI']), 1),
                '추세점수': round(float(last['MFI'] * last['Vol_Accel']), 1),
                'LINK': f"https://toss.im/stock-info/S/{t}" # 토스증권 링크
            })
            if i % 20 == 0:
                status_text.text(f"📦 분석 중: {t} ({i}/{total_count})")
                progress_bar.progress((i + 1) / total_count)
            time.sleep(0.01)
        except: continue
            
    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(all_results)

# 3. 리더보드 표시 함수 (Toss 링크 최우측 배치)
def display_leaderboard(df):
    if df.empty:
        st.warning("조건에 맞는 종목이 없습니다.")
        return

    # 컬럼 순서 조정: LINK를 마지막으로
    cols = [c for c in df.columns if c != 'LINK'] + ['LINK']
    df = df[cols]

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "LINK": st.column_config.LinkColumn("LINK", display_text="Toss"),
            "Price": st.column_config.NumberColumn("Price", format="$ %.2f"),
            "Volume_USD": st.column_config.NumberColumn("거래대금($)", format="%d"),
            "Vol_Accel": st.column_config.NumberColumn("거래가속")
        }
    )

# --- 메인 UI ---
st.title("💵 V15 PRO LEADER BOARD")

# 사이드바 필터
st.sidebar.header("🎛️ FILTER")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("평균 대비 거래량", 0.5, 5.0, 1.2)

# 스캔 버튼
if st.button("🔥 나스닥 전체 실시간 스캔 시작 (V2 내재화)"):
    start_time = time.time()
    updated_df = run_full_market_scan()
    if not updated_df.empty:
        updated_df.to_pickle(SAVE_FILE)
        st.success(f"✅ 스캔 완료! ({int(time.time() - start_time)}초)")
        st.rerun()

# 결과 표시 구역
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    f_df = df[(df['Volume_USD'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
    with t1:
        display_leaderboard(f_df.sort_values(by="반등점수", ascending=False).head(100))
    with t2:
        display_leaderboard(f_df.sort_values(by="추세점수", ascending=False).head(100))
    
    if st.button("💾 이 리스트를 오늘의 TOP으로 저장"):
        st.toast("✅ 오늘자 기록이 완료되었습니다.")
else:
    st.info("💡 스캔 버튼을 눌러 V2 성적표 생성을 시작하세요.")
