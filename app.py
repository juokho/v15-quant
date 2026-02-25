import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

# 다크모드 버튼 및 스타일
st.markdown("""
    <style>
    .dark-mode-btn {
        position: fixed; bottom: 25px; right: 25px; z-index: 9999;
        background-color: #1E1E1E; color: #FFD700; border: 1px solid #444;
        border-radius: 50%; width: 50px; height: 50px; cursor: pointer;
        font-size: 22px; display: flex; align-items: center; justify-content: center;
    }
    </style>
    <script>
    function toggleDarkMode() {
        const body = window.parent.document.querySelector('body');
        const mode = body.getAttribute('data-theme');
        body.setAttribute('data-theme', mode === 'dark' ? 'light' : 'dark');
    }
    </script>
    <div class="dark-mode-btn" onclick="toggleDarkMode()">🌓</div>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_clean.pkl"

# 2. 데이터 스캔 함수
def run_realtime_scan(ticker_list):
    all_results = []
    for t in ticker_list:
        try:
            full_ticker = f"{t}.KS" if t.isdigit() or t in ["GAUZ", "SLNH"] else t
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if df.empty: continue
            
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            last = df.iloc[-1]
            
            # 열 이름을 'Score'로 명확히 고정
            all_results.append({
                'Ticker': t,
                'Price': round(float(last['Close']), 2),
                'RSI': round(float(last['RSI']), 2),
                'MFI': round(float(last['MFI']), 2),
                'Score': round(100 - float(last['RSI']), 2) 
            })
        except: continue
    return pd.DataFrame(all_results)

# 3. 메인 UI
st.title("🏆 V15 PRO QUANT - LEADERBOARD")

if st.button("🔥 START ANALYSIS"):
    with st.spinner("ANALYZING..."):
        target_list = ["AAPL", "TSLA", "NVDA", "GAUZ", "SLNH", "005930", "MSFT"]
        df_real = run_realtime_scan(target_list)
        df_real.to_pickle(SAVE_FILE)
        st.rerun()

if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # [에러 방어] Score 열이 없으면 가짜 데이터라도 생성해서 에러 방지
    if "Score" not in df.columns:
        st.warning("⚠️ 데이터 형식이 변경되었습니다. 상단 버튼을 눌러 스캔을 새로 진행해주세요.")
        df["Score"] = 0 

    grid_cfg = {
        "Ticker": st.column_config.TextColumn("💎 ASSET"),
        "Price": st.column_config.NumberColumn("💵 PRICE", format="$%.2f"),
        "RSI": st.column_config.NumberColumn("📊 RSI", format="%.2f"),
        "MFI": st.column_config.NumberColumn("📈 MFI", format="%.2f"),
        "Score": st.column_config.NumberColumn("🎯 SCORE", format="%.1f")
    }
    
    # 정렬 시 에러 방지를 위해 존재하는 열인지 한 번 더 확인
    sort_key = "Score" if "Score" in df.columns else df.columns[0]
    
    st.dataframe(
        df.sort_values(sort_key, ascending=False),
        column_config=grid_cfg,
        hide_index=True,
        use_container_width=True
    )
else:
    st.info("💡 PRESS START ANALYSIS TO BEGIN.")
