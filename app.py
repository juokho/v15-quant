import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime

# 1. 기본 설정 (다크 테마 지향)
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

# [CSS/JS] 다크모드 전환 및 깔끔한 그리드 디자인
st.markdown("""
    <style>
    /* 다크모드 전환 버튼 (우측 하단 고정) */
    .dark-mode-btn {
        position: fixed;
        bottom: 25px;
        right: 25px;
        z-index: 9999;
        background-color: #1E1E1E;
        color: #FFD700;
        border: 1px solid #444;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        cursor: pointer;
        font-size: 22px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.3);
    }
    .stDataFrame { border: 1px solid #333 !important; }
    </style>
    
    <script>
    function toggleDarkMode() {
        const body = window.parent.document.querySelector('body');
        const currentMode = body.getAttribute('data-theme');
        body.setAttribute('data-theme', currentMode === 'dark' ? 'light' : 'dark');
    }
    </script>
    <div class="dark-mode-btn" onclick="toggleDarkMode()">🌓</div>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_clean.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 2. 데이터 처리 함수 (순수 수치 분석 중심)
def run_realtime_scan(ticker_list):
    all_results = []
    for t in ticker_list:
        try:
            # 한국 종목 및 GAUZ, SLNH 예외 처리
            full_ticker = f"{t}.KS" if t.isdigit() or t in ["GAUZ", "SLNH"] else t
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if df.empty: continue
            
            # 지표 계산
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            last = df.iloc[-1]
            
            all_results.append({
                'Ticker': t,
                'Price': round(float(last['Close']), 2),
                'RSI': round(float(last['RSI']), 2),
                'MFI': round(float(last['MFI']), 2),
                'Score': 100 - float(last['RSI']) # 반등 가능성 점수
            })
        except: continue
    return pd.DataFrame(all_results)

# --- 메인 UI 레이아웃 ---
st.title("🏆 V15 PRO QUANT - LEADERBOARD")
st.caption("Clean Analysis Mode (Pre-Toss Integration)")

# 사이드바 과거 기록
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    st.sidebar.markdown("### 📂 HISTORY")
    selected_date = st.sidebar.selectbox("Select Date", ["None"] + sorted(hist_df['Date'].unique(), reverse=True))
    if selected_date != "None":
        st.table(hist_df[hist_df['Date'] == selected_date][['Ticker', 'Buy_Price']])

st.markdown("---")

# 실시간 분석 터미널
st.subheader("📡 REAL-TIME TERMINAL")
if st.button("🔥 START ANALYSIS"):
    with st.spinner("FETCHING MARKET DATA..."):
        # 관리 종목 리스트
        target_list = ["AAPL", "TSLA", "NVDA", "GAUZ", "SLNH", "005930", "MSFT"]
        df_real = run_realtime_scan(target_list)
        df_real.to_pickle(SAVE_FILE)
        st.rerun()

if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # [설정] 순수 수치 중심 그리드
    grid_cfg = {
        "Ticker": st.column_config.TextColumn("💎 ASSET"),
        "Price": st.column_config.NumberColumn("💵 PRICE", format="$%.2f"),
        "RSI": st.column_config.NumberColumn("📊 RSI", format="%.2f"),
        "MFI": st.column_config.NumberColumn("📈 MFI", format="%.2f"),
        "Score": st.column_config.NumberColumn("🎯 SCORE", format="%.1f")
    }
    
    st.dataframe(
        df.sort_values("Score", ascending=False),
        column_config=grid_cfg,
        hide_index=True,
        use_container_width=True
    )
    
    if st.button("💾 SAVE TOP PICKS"):
        st.toast("✅ SELECTION ARCHIVED.")
else:
    st.info("💡 PRESS START ANALYSIS TO BEGIN.")
