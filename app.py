import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT V3.11", layout="wide")

if not os.path.exists("backdata"):
    os.makedirs("backdata")

LIVE_FILE = "v15_live.pkl"

# [핵심] 단일 종목 분석 함수 (병렬 처리를 위해 분리)
def analyze_ticker(t, date_str, is_live):
    try:
        df = fdr.DataReader(t, end=date_str).tail(60) if not is_live else fdr.DataReader(t).tail(60)
        if len(df) < 30: return None
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        df['Vol_Accel'] = df['Volume'] / df['Volume'].rolling(20).mean()
        
        last = df.iloc[-1]
        return {
            'Ticker': t, 'Price_Val': float(last['Close']),
            '거래대금_Val': int(last['Close'] * last['Volume']),
            'Vol_Accel': float(last['Vol_Accel']),
            '반등점수': round(100 - float(last['RSI']), 1),
            '추세점수': round(float(last['MFI'] * last['Vol_Accel']), 1),
            'Toss': f"https://toss.im/stock-info/S/{t.upper()}"
        }
    except: return None

# 2. 스캔 함수 (ThreadPoolExecutor 적용으로 획기적 단축)
def run_scan(target_date=None, silent=False):
    all_results = []
    is_live = target_date is None
    date_str = datetime.now().strftime('%Y-%m-%d') if is_live else target_date.strftime('%Y-%m-%d')
    save_path = LIVE_FILE if is_live else f"backdata/v15_{date_str}.pkl"
    
    if not is_live and os.path.exists(save_path) and silent:
        return None

    try:
        df_nasdaq = fdr.StockListing('NASDAQ')
        tickers = df_nasdaq['Symbol'].tolist()
    except: return pd.DataFrame()

    # --- 병렬 처리 구간 (Turbo) ---
    with ThreadPoolExecutor(max_workers=15) as executor: # 15개씩 동시 처리
        future_to_ticker = {executor.submit(analyze_ticker, t, date_str, is_live): t for t in tickers}
        
        # 스캔 상황 표시용 (silent 모드가 아닐 때만)
        if not silent:
            progress_bar = st.progress(0)
            status_text = st.empty()
            count = 0
            for future in as_completed(future_to_ticker):
                res = future.result()
                if res: all_results.append(res)
                count += 1
                if count % 50 == 0:
                    progress_bar.progress(count / len(tickers))
                    status_text.text(f"🚀 분석 중... ({count}/{len(tickers)})")
        else:
            for future in as_completed(future_to_ticker):
                res = future.result()
                if res: all_results.append(res)
    # ----------------------------
            
    res_df = pd.DataFrame(all_results)
    if not res_df.empty:
        res_df.to_pickle(save_path)
    return res_df

# [이하 UI 및 출력 로직은 V3.10과 동일 유지]
def display_board(df, score_col):
    display_df = df.copy()
    display_df['Price'] = display_df['Price_Val'].apply(lambda x: f"${x:,.2f}")
    display_df['거래대금'] = display_df['거래대금_Val'].apply(lambda x: f"${x:,}")
    
    # 랭킹 표시를 위한 정렬
    display_df = display_df.sort_values(score_col, ascending=False).head(100)
    
    actual_cols = ['Ticker', 'Price', '거래대금', 'Vol_Accel', score_col, 'Toss']
    st.dataframe(display_df[actual_cols], use_container_width=True, hide_index=True,
                 column_config={"Toss": st.column_config.LinkColumn("Toss", display_text="🚀")})

st.title("💵 V15 PRO QUANT V3.11 (Turbo)")

mode = st.sidebar.radio("📡 모드 선택", ["실시간 스캔", "과거 백데이터 분석", "데이터 일괄 수집"])

if mode == "데이터 일괄 수집":
    st.header("📂 2월 전체 데이터 고속 수집")
    if st.button("🚀 Turbo 모드로 2월 수집 시작"):
        start_date = datetime(2026, 2, 1)
        end_date = datetime.now()
        current = start_date
        while current <= end_date:
            if current.weekday() < 5:
                st.write(f"🔥 {current.strftime('%Y-%m-%d')} 고속 수집 중...")
                run_scan(current, silent=True)
            current += timedelta(days=1)
        st.success("✅ 모든 데이터 수집 완료!")

elif mode == "과거 백데이터 분석":
    selected_date = st.date_input("조회할 날짜", value=datetime.now() - timedelta(days=1))
    path = f"backdata/v15_{selected_date.strftime('%Y-%m-%d')}.pkl"
    if os.path.exists(path):
        df = pd.read_pickle(path)
        t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
        with t1: display_board(df, '반등점수')
        with t2: display_board(df, '추세점수')
    else: st.warning("데이터가 없습니다. 수집을 먼저 해주세요.")

else: # 실시간
    if st.button("🔥 실시간 Turbo 스캔"):
        run_scan(None)
        st.rerun()
    if os.path.exists(LIVE_FILE):
        df = pd.read_pickle(LIVE_FILE)
        t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
        with t1: display_board(df, '반등점수')
        with t2: display_board(df, '추세점수')
