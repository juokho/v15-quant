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

# 2. 전체 시장 스캔 함수 (블랙리스트/특정 종목 언급 없음)
def run_full_market_scan():
    all_results = []
    with st.spinner("📡 나스닥(NASDAQ) 전 종목 분석 중..."):
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

# 3. 백테스트 기록 저장 함수
def record_to_history(df):
    today = datetime.now().strftime("%Y-%m-%d")
    new_records = []
    
    p_top5 = df.sort_values(by="반등점수", ascending=False).head(5)
    a_top5 = df.sort_values(by="추세점수", ascending=False).head(5)
    
    for _, row in p_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': '바닥반등', 'Ticker': row['Ticker'], 'Buy_Price': row['Price_Val']})
    for _, row in a_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': '상승추세', 'Ticker': row['Ticker'], 'Buy_Price': row['Price_Val']})
    
    new_df = pd.DataFrame(new_records)
    if os.path.exists(TRACKER_FILE):
        old_df = pd.read_csv(TRACKER_FILE)
        old_df = old_df[old_df['Date'] != today]
        final_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        final_df = new_df
    final_df.to_csv(TRACKER_FILE, index=False)
    st.toast(f"✅ {today} 상위 종목 기록 완료!")

# 4. 리더보드 출력 함수 ($ 및 콤마 강제 적용)
def display_formatted_df(df, score_col):
    if df.empty:
        st.warning("🧐 조건에 맞는 종목이 없습니다.")
        return

    display_df = df.copy()
    display_df['Price'] = display_df['Price_Val'].apply(lambda x: f"${x:,.2f}")
    display_df['거래대금'] = display_df['거래대금_Val'].apply(lambda x: f"${x:,}")
    
    target_cols = ['Ticker', 'Price', '거래대금', 'Vol_Accel', score_col, 'Toss']
    
    st.dataframe(
        display_df[target_cols],
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
st.title("💵 V15 PRO LEADER BOARD")

st.sidebar.header("🎛️ FILTER")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("평균 대비 거래량", 0.5, 5.0, 1.2)

st.sidebar.markdown("---")
st.sidebar.header("📂 과거 기록 (백테스트)")
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    available_dates = sorted(hist_df['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("📅 날짜 선택", ["선택 안 함"] + available_dates)
else:
    selected_date = "선택 안 함"

if st.button("🔥 나스닥 전체 실시간 스캔 시작 (V3.6)"):
    updated_df = run_full_market_scan()
    if not updated_df.empty:
        updated_df.to_pickle(SAVE_FILE)
        st.success("✅ 스캔 완료!")
        st.rerun()

# 백테스트 섹션
if selected_date != "선택 안 함":
    st.subheader(f"📅 {selected_date} Pick 수익률 추적")
    target_picks = hist_df[hist_df['Date'] == selected_date].copy()
    if st.button("📈 실시간 수익률 확인"):
        for idx, row in target_picks.iterrows():
            try:
                curr_price = fdr.DataReader(row['Ticker']).iloc[-1]['Close']
                target_picks.at[idx, 'Price'] = float(curr_price)
            except: target_picks.at[idx, 'Price'] = 0
        target_picks['수익률(%)'] = ((target_picks['Price'] - target_picks['Buy_Price']) / target_picks['Buy_Price'] * 100).round(2)
        st.table(target_picks[['Strategy', 'Ticker', 'Buy_Price', 'Price', '수익률(%)']])
    else:
        st.table(target_picks)

# 메인 결과 표시 (KeyError 방어 로직 강화)
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # [안전 패치] 어떤 컬럼명이든 필터링용 규격으로 강제 변환
    if 'Price_Val' not in df.columns:
        df['Price_Val'] = df['Price'] if 'Price' in df.columns else 0.0
    
    if '거래대금_Val' not in df.columns:
        # '거래대금'이 없으면 'Volume_USD'를 찾고, 그것도 없으면 0으로 처리
        if '거래대금' in df.columns:
            df['거래대금_Val'] = df['거래대금']
        elif 'Volume_USD' in df.columns:
            df['거래대금_Val'] = df['Volume_USD']
        else:
            df['거래대금_Val'] = 0

    # 필터 적용
    f_df = df[(df['거래대금_Val'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
    with t1:
        p_df = f_df.sort_values(by="반등점수", ascending=False).head(100)
        display_formatted_df(p_df, "반등점수")
    with t2:
        a_df = f_df.sort_values(by="추세점수", ascending=False).head(100)
        display_formatted_df(a_df, "추세점수")
    
    if st.button("💾 이 리스트를 오늘의 TOP으로 저장"):
        record_to_history(df)
else:
    st.info("💡 스캔 버튼을 눌러 리더보드를 생성하세요.")
