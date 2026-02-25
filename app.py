import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
import time
from datetime import datetime

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 2. 스캔 함수 (안전한 열 이름 생성)
def run_full_market_scan():
    all_results = []
    with st.spinner("📡 나스닥(NASDAQ) 리스트 분석 중..."):
        try:
            df_nasdaq = fdr.StockListing('NASDAQ')
            exclude = ['GAUZ', 'SLNH'] # 집중 관리 종목 제외
            tickers = [t for t in df_nasdaq['Symbol'].tolist() if t not in exclude]
        except: return pd.DataFrame()

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
                'Price': float(last['Close']), # 원본 숫자 데이터 유지
                '거래대금': int(last['Close'] * last['Volume']),
                'Vol_Accel': float(last['Vol_Accel']),
                '반등점수': 100 - float(last['RSI']),
                '추세점수': float(last['MFI'] * last['Vol_Accel'])
            })
            if i % 20 == 0: progress_bar.progress((i + 1) / len(tickers))
        except: continue
    progress_bar.empty()
    return pd.DataFrame(all_results)

# 3. 데이터 표시 최적화 (에러 발생한 포맷 코드 수정)
def display_formatted_df(df, score_col):
    # 에러 방지용 포맷팅: $와 소수점 둘째자리만 지정 (콤마는 자동 적용 시도)
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn("Price", format="$%.2f"),
            "거래대금": st.column_config.NumberColumn("거래대금", format="$%d"),
            "Vol_Accel": st.column_config.NumberColumn("거래가속", format="%.2f"),
            score_col: st.column_config.NumberColumn(score_col, format="%.1f")
        }
    )

# --- 메인 UI ---
st.title("💵 V15 PRO LEADER BOARD")

st.sidebar.header("🎛️ FILTER")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("평균 대비 거래량", 0.5, 5.0, 1.2)

if st.button("🔥 나스닥 실시간 스캔 시작 (V2.7)"):
    updated_df = run_full_market_scan()
    if not updated_df.empty:
