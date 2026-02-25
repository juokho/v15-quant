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

# 2. 전체 시장 스캔 함수 (블랙리스트 로직 완전 제거)
def run_full_market_scan():
    all_results = []
    with st.spinner("📡 나스닥(NASDAQ) 리스트 분석 중..."):
        try:
            df_nasdaq = fdr.StockListing('NASDAQ')
            tickers = df_nasdaq['Symbol'].tolist()
        except Exception as e:
            st.error(f"리스트 확보 실패: {e}")
            return pd.DataFrame()

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
                'Price_Val': float(last['Close']), # 계산용 숫자
                '거래대금_Val': int(last['Close'] * last['Volume']), # 계산용 숫자
                'Vol_Accel': float(last['Vol_Accel']),
                '반등점수': round(100 - float(last['RSI']), 1),
                '추세점수': round(float(last['MFI'] * last['Vol_Accel']), 1)
            })
            if i % 20 == 0:
                progress_bar.progress((i + 1) / total_count)
            time.sleep(0.01)
        except: continue
            
    progress_bar.empty()
    return pd.DataFrame(all_results)

# 3. 데이터 포맷팅 및 출력 함수 (콤마 및 $ 강제 적용)
def display_formatted_df(df, score_col):
    # 출력을 위해 데이터를 문자열로 변환 ($, 콤마 강제 삽입)
    display_df = df.copy()
    display_df['Price'] = display_df['Price_Val'].apply(lambda x: f"${x:,.2f}")
    display_df['거래대금'] = display_df['거래대금_Val'].apply(lambda x: f"${x:,}")
    
    # 보기 좋게 열 순서 재배치
    cols = ['Ticker', 'Price', '거래대금', 'Vol_Accel', score_col]
    
    st.dataframe(
        display_df[cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Vol_Accel": st.column_config.NumberColumn("거래가속", format="%.2f"),
            score_col: st.column_config.NumberColumn(score_col, format="%.1f")
        }
    )

# --- 메인 UI ---
st.title("💵 V15 PRO LEADER BOARD")

st.sidebar.header("🎛️ FILTER")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("평균 대비 거래량", 0.5, 5.0, 1.2)

if st.button("🔥 나스닥 실시간 스캔 시작 (V3.1)"):
    start_time = time.time()
    updated_df = run_full_market_scan()
    if not updated_df.empty:
        updated_df.to_pickle(SAVE_FILE)
        st.success(f"✅ 스캔 완료!")
        st.rerun()

if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # 과거 데이터 호환용 필드 확인
    if '거래대금_Val' not in df.columns:
        df['거래대금_Val'] = df['거래대금'] if '거래대금' in df.columns else 0
    if 'Price_Val' not in df.columns:
        df['Price_Val'] = df['Price'] if 'Price' in df.columns else 0
    
    # 필터 적용
    f_df = df[(df['거래대금_Val'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
    with t1:
        p_df = f_df.sort_values(by="반등점수", ascending=False).head(100)
        display_formatted_df(p_df, "반등점수")
    with t2:
        a_df = f_df.sort_values(by="추세점수", ascending=False).head(100)
        display_formatted_df(a_df, "추세점수")
else:
    st.info("💡 스캔 버튼을 눌러 성적표 생성을 시작하세요.")
