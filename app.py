import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime

# 1. 기본 설정 및 폰트 스타일링
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif !important; }
    h1 { font-weight: 800 !important; letter-spacing: -1px; }
    </style>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"
FOCUS_TICKERS = ["GAUZ", "SLNH"] 

# 2. 데이터 업데이트 및 스캔 함수
def run_realtime_scan(ticker_list):
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(ticker_list):
        try:
            full_ticker = f"{t}.KS" if t in ["005930", "GAUZ", "SLNH"] else t
            status_text.text(f"🔍 스캔 중: {full_ticker} ({i+1}/{len(ticker_list)})")
            
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if len(df) < 20: continue

            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            
            avg_vol = df['Volume'].rolling(20).mean()
            df['Vol_Accel'] = df['Volume'] / avg_vol
            df['Avg_Range'] = (abs(df['High'] - df['Low']) / df['Close'] * 100).rolling(20).mean()
            
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t,
                'Price': round(float(last['Close']), 2), # "현재가" 대신 "Price"
                'RSI': round(float(last['RSI']), 2),
                'MFI': round(float(last['MFI']), 2),
                'Vol_Accel': round(float(last['Vol_Accel']), 2),
                'Avg_Range': round(float(last['Avg_Range']), 2),
                'Volume_USD': float(last['Close'] * last['Volume']),
                '반등점수': 100 - float(last['RSI']),
                '추세점수': float(last['MFI'] * last['Vol_Accel'])
            })
        except: continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    status_text.empty()
    return pd.DataFrame(all_results)

# 3. 메인 UI
st.title("🛡️ V15 PRO - 전광판 & 백테스트")

# 사이드바 필터
st.sidebar.header("🎛️ 오늘의 전광판 필터")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("최소 거래 가속도", 0.5, 5.0, 1.0)

# [V1.1 수정] 강제 초기화 버튼
if st.sidebar.button("⚠️ 데이터 초기화 (에러 발생 시)"):
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
    st.rerun()

if st.button("🔥 실시간 전종목 스캔 시작"):
    sample_list = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "GAUZ", "SLNH", "005930"]
    updated_df = run_realtime_scan(sample_list)
    updated_df.to_pickle(SAVE_FILE)
    st.rerun()

# [V1.1 수정] 데이터 로드 시 열 검사 로직 추가
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # 만약 불러온 데이터에 'Volume_USD'가 없다면 에러 방지
    if 'Volume_USD' not in df.columns or 'Vol_Accel' not in df.columns:
        st.error("⚠️ 데이터 구조가 다릅니다. 왼쪽 사이드바의 [데이터 초기화]를 누르거나 스캔을 다시 해주세요.")
        st.stop()

    f_df = df[(df['Volume_USD'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔵 Phoenix (반등)", "🟣 Alpha (추세)"])
    with t1:
        st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(50), use_container_width=True)
    with t2:
        st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(50), use_container_width=True)
else:
    st.info("💡 스캔 시작 버튼을 눌러주세요.")
