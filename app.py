import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime, timedelta

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

# [핵심 수정] 다크모드 자바스크립트 및 버튼
st.markdown("""
    <style>
    .dark-mode-btn {
        position: fixed;
        bottom: 30px;
        right: 30px;
        z-index: 9999;
        background-color: #1E1E1E;
        color: #FFD700;
        border: 2px solid #333;
        border-radius: 50%;
        width: 50px;
        height: 50px;
        cursor: pointer;
        font-size: 20px;
    }
    </style>
    <script>
    function toggleDarkMode() {
        const body = window.parent.document.querySelector('body');
        const currentMode = body.getAttribute('data-theme');
        body.setAttribute('data-theme', currentMode === 'dark' ? 'light' : 'dark');
    }
    </script>
    <button class="dark-mode-btn" onclick="toggleDarkMode()">🌓</button>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# [에러 해결 포인트] 삼중 따옴표로 감싸서 문자열 끊김 방지
TOSS_LOGO_B64 = """data:image/jpeg;base64,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"""

# 2. 데이터 처리
def run_realtime_scan(ticker_list):
    all_results = []
    for t in ticker_list:
        try:
            full_ticker = f"{t}.KS" if t.isdigit() or t in ["GAUZ", "SLNH"] else t
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if df.empty: continue
            df['RSI'] = ta.rsi(df['Close'], length=14)
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t, 'Price': round(float(last['Close']), 2),
                'RSI': round(float(last['RSI']), 2),
                'TOSS_LOGO': TOSS_LOGO_B64,
                'TOSS_LINK': f"https://tossinvest.com/stocks/{t}",
                'Score': 100 - float(last['RSI'])
            })
        except: continue
    return pd.DataFrame(all_results)

# 3. UI 레이아웃
st.title("🏆 V15 PRO QUANT - LEADERBOARD")

# 사이드바
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    selected_date = st.sidebar.selectbox("📂 HISTORY", ["None"] + sorted(hist_df['Date'].unique(), reverse=True))
    if selected_date != "None":
        st.table(hist_df[hist_df['Date'] == selected_date][['Ticker', 'Buy_Price']])

st.markdown("---")

# 실시간 터미널
st.subheader("📡 REAL-TIME TERMINAL")
if st.button("🔥 START SCAN"):
    with st.spinner("SCANNING..."):
        target_list = ["AAPL", "TSLA", "NVDA", "GAUZ", "SLNH", "005930", "MSFT"]
        df_real = run_realtime_scan(target_list)
        df_real.to_pickle(SAVE_FILE)
        st.rerun()

if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    cfg = {
        "Ticker": st.column_config.TextColumn("💎 ASSET"),
        "Price": st.column_config.NumberColumn("💵 PRICE", format="$%.2f"),
        "TOSS_LOGO": st.column_config.ImageColumn("📲 TOSS"),
        "TOSS_LINK": st.column_config.LinkColumn("🔗 TRADE", display_text="GO"),
        "RSI": st.column_config.NumberColumn("📊 RSI", format="%.2f")
    }
    st.dataframe(df[['Ticker', 'Price', 'TOSS_LOGO', 'TOSS_LINK', 'RSI']], 
                 column_config=cfg, hide_index=True, use_container_width=True)
