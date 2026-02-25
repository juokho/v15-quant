import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
import time
from datetime import datetime, timedelta

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 2. 타임머신 스캔 함수 (과거 특정 날짜 기준 스캔)
def run_historical_scan(target_date):
    all_results = []
    # target_date는 datetime 객체
    date_str = target_date.strftime('%Y-%m-%d')
    
    with st.spinner(f"📡 {date_str} 기준 나스닥 데이터 분석 중..."):
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
            # 해당 날짜까지의 데이터를 가져옴
            df = fdr.DataReader(t, end=date_str).tail(60)
            if len(df) < 30: continue

            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            df['Vol_Accel'] = df['Volume'] / df['Volume'].rolling(20).mean()
            
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t,
                'Price_Val': float(last['Close']),
                '거래대금_Val': int(last['Close'] * last['Volume']),
                'Vol_Accel': float(last['Vol_Accel']),
                '반등점수': round(100 - float(last['RSI']), 1),
                '추세점수': round(float(last['MFI'] * last['Vol_Accel']), 1),
                'Toss': f"https://toss.im/stock-info/S/{t.upper()}"
            })
            if i % 20 == 0:
                progress_bar.progress((i + 1) / total_count)
            time.sleep(0.01)
        except: continue
            
    progress_bar.empty()
    return pd.DataFrame(all_results)

# 3. 리더보드 출력 함수 (V3 포맷팅 유지)
def display_formatted_df(df, score_col):
    if df.empty:
        st.warning("🧐 조건에 맞는 종목이 없습니다.")
        return

    display_df = df.copy()
    if 'Price_Val' in display_df.columns:
        display_df['Price'] = display_df['Price_Val'].apply(lambda x: f"${x:,.2f}")
    if '거래대금_Val' in display_df.columns:
        display_df['거래대금'] = display_df['거래대금_Val'].apply(lambda x: f"${x:,}")
    
    possible_cols = ['Ticker', 'Price', '거래대금', 'Vol_Accel', score_col, 'Toss']
    actual_cols = [c for c in possible_cols if c in display_df.columns]
    
    st.dataframe(
        display_df[actual_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Price": st.column_config.TextColumn("Price"),
            "거래대금": st.column_config.TextColumn("거래대금"),
            "Vol_Accel": st.column_config.NumberColumn("거래가속", format="%.2f"),
            score_col: st.column_config.NumberColumn(score_col, format="%.1f"),
            "Toss": st.column_config.LinkColumn("Toss", display_text="🚀")
        }
    )

# --- 메인 UI ---
st.title("💵 V15 PRO LEADER BOARD (Time Machine)")

# 사이드바: 타임머신 설정
st.sidebar.header("🕒 타임머신 스캔")
# 현재 날짜로부터 한 달 전까지 선택 가능
max_date = datetime.now()
min_date = max_date - timedelta(days=30)
selected_scan_date = st.sidebar.date_input("스캔할 과거 날짜 선택", value=max_date, min_value=min_date, max_value=max_date)

if st.sidebar.button("🕰️ 해당 날짜 리더보드 생성"):
    hist_scan_result = run_historical_scan(selected_scan_date)
    if not hist_scan_result.empty:
        hist_scan_result.to_pickle(SAVE_FILE)
        st.success(f"✅ {selected_scan_date} 기준 데이터 복구 완료!")
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("🎛️ FILTER")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("평균 대비 거래량", 0.5, 5.0, 1.2)

# 메인 결과 표시 로직 (V3 유지)
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # 안전 패치 (KeyError 방어)
    if 'Price_Val' not in df.columns: df['Price_Val'] = df['Price'] if 'Price' in df.columns else 0.0
    if '거래대금_Val' not in df.columns:
        if '거래대금' in df.columns: df['거래대금_Val'] = df['거래대금']
        elif 'Volume_USD' in df.columns: df['거래대금_Val'] = df['Volume_USD']
        else: df['거래대금_Val'] = 0
    if 'Toss' not in df.columns: df['Toss'] = df['Ticker'].apply(lambda x: f"https://toss.im/stock-info/S/{str(x).upper()}")
    if 'Vol_Accel' not in df.columns: df['Vol_Accel'] = 0.0

    f_df = df[(df['거래대금_Val'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
    with t1:
        p_df = f_df.sort_values(by="반등점수", ascending=False).head(100)
        display_formatted_df(p_df, "반등점수")
    with t2:
        a_df = f_df.sort_values(by="추세점수", ascending=False).head(100)
        display_formatted_df(a_df, "추세점수")
else:
    st.info("💡 사이드바에서 날짜를 선택하고 '타임머신 스캔'을 시작하세요.")
