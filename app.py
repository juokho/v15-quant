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

# 2. 스캔 함수 (항상 새로운 열 이름을 보장)
def run_full_market_scan():
    all_results = []
    with st.spinner("📡 나스닥(NASDAQ) 전체 리스트 확보 중..."):
        try:
            df_nasdaq = fdr.StockListing('NASDAQ')
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
                'Price': round(float(last['Close']), 2),
                '거래대금': int(last['Close'] * last['Volume']), # 열 이름 확정
                'Vol_Accel': round(float(last['Vol_Accel']), 2),
                '반등점수': round(100 - float(last['RSI']), 1),
                '추세점수': round(float(last['MFI'] * last['Vol_Accel']), 1)
            })
            if i % 20 == 0:
                status_text.text(f"📦 분석 중: {t} ({i}/{total_count})")
                progress_bar.progress((i + 1) / total_count)
            time.sleep(0.01)
        except: continue
            
    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(all_results)

# 3. 데이터 표시 최적화 함수
def display_formatted_df(df, score_col):
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.NumberColumn("Price", format="$ %,.2f"),
            "거래대금": st.column_config.NumberColumn("거래대금", format="$ %,d"),
            "Vol_Accel": st.column_config.NumberColumn("거래가속", format="%.2f"),
            score_col: st.column_config.NumberColumn(score_col, format="%.1f")
        }
    )

# --- 메인 UI ---
st.title("💵 V15 PRO LEADER BOARD")

st.sidebar.header("🎛️ FILTER")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("평균 대비 거래량", 0.5, 5.0, 1.2)

if st.button("🔥 나스닥 전체 실시간 스캔 시작 (내재화)"):
    start_time = time.time()
    updated_df = run_full_market_scan()
    if not updated_df.empty:
        updated_df.to_pickle(SAVE_FILE)
        st.success("✅ 스캔 완료! 데이터가 업데이트되었습니다.")
        st.rerun()

# 에러 방지 구역: 파일이 있어도 열 이름이 다르면 에러 처리
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # [안전 패치] 만약 예전 파일이라 '거래대금' 열이 없으면 'Volume_USD'를 찾아서 바꿔줌
    if '거래대금' not in df.columns and 'Volume_USD' in df.columns:
        df = df.rename(columns={'Volume_USD': '거래대금'})
    
    try:
        f_df = df[(df['거래대금'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
        
        t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
        with t1:
            p_df = f_df.sort_values(by="반등점수", ascending=False).head(100)
            display_formatted_df(p_df[['Ticker', 'Price', '거래대금', 'Vol_Accel', '반등점수']], "반등점수")
        with t2:
            a_df = f_df.sort_values(by="추세점수", ascending=False).head(100)
            display_formatted_df(a_df[['Ticker', 'Price', '거래대금', 'Vol_Accel', '추세점수']], "추세점수")
    except KeyError:
        st.error("⚠️ 데이터 형식이 변경되었습니다. [스캔 시작] 버튼을 눌러 데이터를 갱신해주세요.")
else:
    st.info("💡 스캔 버튼을 눌러 성적표를 만듭니다.")
