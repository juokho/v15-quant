import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
import time
from datetime import datetime, timedelta

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT V3.10", layout="wide")

# 폴더 생성 (데이터 관리용)
if not os.path.exists("backdata"):
    os.makedirs("backdata")

LIVE_FILE = "v15_live.pkl"

# 2. 스캔 함수 (날짜별 개별 저장 지원)
def run_scan(target_date=None, silent=False):
    all_results = []
    is_live = target_date is None
    date_str = datetime.now().strftime('%Y-%m-%d') if is_live else target_date.strftime('%Y-%m-%d')
    save_path = LIVE_FILE if is_live else f"backdata/v15_{date_str}.pkl"
    
    # 이미 데이터가 있으면 건너뛰기 (일괄 수집용)
    if not is_live and os.path.exists(save_path) and silent:
        return None

    try:
        df_nasdaq = fdr.StockListing('NASDAQ')
        tickers = df_nasdaq['Symbol'].tolist()
    except: return pd.DataFrame()

    for t in tickers:
        try:
            df = fdr.DataReader(t, end=date_str).tail(60) if not is_live else fdr.DataReader(t).tail(60)
            if len(df) < 30: continue
            
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            df['Vol_Accel'] = df['Volume'] / df['Volume'].rolling(20).mean()
            
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t, 'Price_Val': float(last['Close']),
                '거래대금_Val': int(last['Close'] * last['Volume']),
                'Vol_Accel': float(last['Vol_Accel']),
                '반등점수': round(100 - float(last['RSI']), 1),
                '추세점수': round(float(last['MFI'] * last['Vol_Accel']), 1),
                'Toss': f"https://toss.im/stock-info/S/{t.upper()}"
            })
        except: continue
            
    res_df = pd.DataFrame(all_results)
    if not res_df.empty:
        res_df.to_pickle(save_path)
    return res_df

# 3. 출력 및 수익률 로직 (V3.9 기반 고도화)
def display_board(df, score_col):
    display_df = df.copy()
    display_df['Price'] = display_df['Price_Val'].apply(lambda x: f"${x:,.2f}")
    display_df['거래대금'] = display_df['거래대금_Val'].apply(lambda x: f"${x:,}")
    
    # 수익률 표시 (현재가와 비교 가능할 경우)
    if st.sidebar.checkbox("실시간 수익률 대조 (데이터 로딩 발생)"):
        # 간략화를 위해 상위 20개만 실시간 대조
        top_df = display_df.sort_values(score_col, ascending=False).head(20).copy()
        returns = []
        for t in top_df['Ticker']:
            try:
                curr = fdr.DataReader(t).iloc[-1]['Close']
                gain = ((curr - top_df.loc[top_df['Ticker']==t, 'Price_Val'].values[0]) / top_df.loc[top_df['Ticker']==t, 'Price_Val'].values[0]) * 100
                returns.append(round(gain, 2))
            except: returns.append(0)
        top_df['수익률'] = [f"{r:+.2f}%" for r in returns]
        actual_cols = ['Ticker', 'Price', '수익률', '거래대금', score_col, 'Toss']
        st.dataframe(top_df[actual_cols], use_container_width=True, hide_index=True, 
                     column_config={"Toss": st.column_config.LinkColumn("Toss", display_text="🚀")})
    else:
        actual_cols = ['Ticker', 'Price', '거래대금', 'Vol_Accel', score_col, 'Toss']
        st.dataframe(display_df[actual_cols], use_container_width=True, hide_index=True,
                     column_config={"Toss": st.column_config.LinkColumn("Toss", display_text="🚀")})

# --- 메인 UI ---
st.title("💵 V15 PRO QUANT V3.10")

mode = st.sidebar.radio("📡 모드 선택", ["실시간 스캔", "과거 백데이터 분석", "데이터 일괄 수집"])

if mode == "데이터 일괄 수집":
    st.header("📂 2월 전체 데이터 일괄 수집 (백데이터 구축)")
    st.write("2월 1일부터 오늘까지의 데이터를 날짜별로 수집합니다. 이미 수집된 날짜는 건너뜁니다.")
    if st.button("🚀 2월 데이터 전체 수집 시작"):
        start_date = datetime(2026, 2, 1)
        end_date = datetime.now()
        current = start_date
        while current <= end_date:
            if current.weekday() < 5: # 주말 제외
                st.write(f"🔄 {current.strftime('%Y-%m-%d')} 처리 중...")
                run_scan(current, silent=True)
            current += timedelta(days=1)
        st.success("✅ 2월 백데이터 구축 완료!")

elif mode == "과거 백데이터 분석":
    selected_date = st.date_input("조회할 날짜", value=datetime.now() - timedelta(days=1))
    date_str = selected_date.strftime('%Y-%m-%d')
    path = f"backdata/v15_{date_str}.pkl"
    
    if os.path.exists(path):
        st.subheader(f"📅 {date_str} 리더보드 (로컬 저장소)")
        df = pd.read_pickle(path)
        t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
        with t1: display_board(df, '반등점수')
        with t2: display_board(df, '추세점수')
    else:
        st.warning(f"⚠️ {date_str} 데이터가 없습니다. 먼저 스캔하거나 일괄 수집을 진행하세요.")

else: # 실시간 스캔
    if st.button("🔥 실시간 스캔"):
        run_scan(None)
        st.rerun()
    if os.path.exists(LIVE_FILE):
        df = pd.read_pickle(LIVE_FILE)
        t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
        with t1: display_board(df, '반등점수')
        with t2: display_board(df, '추세점수')
