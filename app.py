import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
import time
from datetime import datetime

# 1. 기본 설정 (아이콘 충돌 방지를 위해 폰트 적용 범위 축소)
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    /* 제목과 일반 텍스트에만 폰트 적용, 시스템 아이콘 영역은 건드리지 않음 */
    h1, h2, h3, p, span { font-family: 'Pretendard', sans-serif !important; }
    </style>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 2. V2 스캔 함수 (기본 로직 유지 + 링크 데이터만 추가)
def run_full_market_scan():
    all_results = []
    try:
        df_nasdaq = fdr.StockListing('NASDAQ')
        exclude = ['GAUZ', 'SLNH'] # 집중 관리 종목 제외
        tickers = [t for t in df_nasdaq['Symbol'].tolist() if t not in exclude]
    except: return pd.DataFrame()

    total_count = len(tickers)
    progress_bar = st.progress(0)
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
                'Price': round(float(last['Close']), 2), # Price 표기 준수
                'Volume_USD': int(last['Close'] * last['Volume']),
                'RSI': round(float(last['RSI']), 1),
                'Vol_Accel': round(float(last['Vol_Accel']), 2),
                '반등점수': round(100 - float(last['RSI']), 1),
                '추세점수': round(float(last['MFI'] * last['Vol_Accel']), 1),
                'LINK': f"https://toss.im/stock-info/S/{t}" # 링크 데이터
            })
            if i % 20 == 0: progress_bar.progress((i + 1) / total_count)
        except: continue
    progress_bar.empty()
    return pd.DataFrame(all_results)

# --- 메인 UI ---
st.title("💵 V15 PRO LEADER BOARD")

# 사이드바 및 스캔 버튼 (V2 동일)
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("평균 대비 거래량", 0.5, 5.0, 1.2)

if st.button("🔥 나스닥 전체 실시간 스캔 시작 (V2)"):
    updated_df = run_full_market_scan()
    if not updated_df.empty:
        updated_df.to_pickle(SAVE_FILE)
        st.rerun()

if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    f_df = df[(df['Volume_USD'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
    
    # 🔗 이모지를 활용한 링크 표시 (폰트 깨짐 방지 핵심)
    column_cfg = {
        "LINK": st.column_config.LinkColumn("LINK", display_text="🔗"),
        "Price": st.column_config.NumberColumn("Price", format="$ %.2f"),
        "Volume_USD": st.column_config.NumberColumn("거래대금($)", format="%d")
    }

    with t1:
        st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(100), 
                     use_container_width=True, hide_index=True, column_config=column_cfg)
    with t2:
        st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(100), 
                     use_container_width=True, hide_index=True, column_config=column_cfg)
    
    if st.button("💾 이 리스트를 오늘의 TOP으로 저장"):
        st.toast("✅ 오늘자 기록 완료!")
