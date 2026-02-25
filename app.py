import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime, timedelta

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")
SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 2. 실시간 스캔 함수
def run_realtime_scan(ticker_list):
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(ticker_list):
        try:
            full_ticker = f"{t}.KS" if t.isdigit() or t in ["GAUZ", "SLNH"] else t
            status_text.text(f"🔍 스캔 중: {full_ticker} ({i+1}/{len(ticker_list)})")
            
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if df.empty or len(df) < 20: continue

            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            
            avg_vol = df['Volume'].rolling(20).mean()
            df['Vol_Accel'] = df['Volume'] / avg_vol
            df['Avg_Range'] = (abs(df['High'] - df['Low']) / df['Close'] * 100).rolling(20).mean()
            
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t,
                'Price': round(float(last['Close']), 2),
                'RSI': round(float(last['RSI']), 2),
                'MFI': round(float(last['MFI']), 2),
                'Vol_Accel': round(float(last['Vol_Accel']), 2),
                'Avg_Range': round(float(last['Avg_Range']), 2),
                'Volume_USD': float(last['Close'] * last['Volume']),
                '반등점수': 100 - float(last['RSI']),
                '추세점수': float(last['MFI'] * last['Vol_Accel']),
                'TOSS': f"https://tossinvest.com/stocks/{t}" 
            })
        except: continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    status_text.empty()
    return pd.DataFrame(all_results)

# 3. 기록 저장 함수
def record_top_picks(df):
    today = datetime.now().strftime("%Y-%m-%d")
    new_records = []
    
    # 열 존재 여부 확인 후 안전하게 정렬
    if '반등점수' in df.columns:
        p_top5 = df.sort_values(by="반등점수", ascending=False).head(5)
        for _, row in p_top5.iterrows():
            new_records.append({'Date': today, 'Strategy': 'Phoenix', 'Ticker': row['Ticker'], 'Buy_Price': row['Price']})
    
    if '추세점수' in df.columns:
        a_top5 = df.sort_values(by="추세점수", ascending=False).head(5)
        for _, row in a_top5.iterrows():
            new_records.append({'Date': today, 'Strategy': 'Alpha', 'Ticker': row['Ticker'], 'Buy_Price': row['Price']})
    
    if new_records:
        new_df = pd.DataFrame(new_records)
        if os.path.exists(TRACKER_FILE):
            old_df = pd.read_csv(TRACKER_FILE)
            old_df = old_df[old_df['Date'] != today]
            final_df = pd.concat([old_df, new_df], ignore_index=True)
        else:
            final_df = new_df
        final_df.to_csv(TRACKER_FILE, index=False)
        st.toast(f"✅ {today} 상위 종목 기록 완료!")

# --- UI 레이아웃 ---
st.title("🛡️ V15 PRO QUANT - 통합 시스템")

# [핵심 수정] 에러 방지용 데이터 클리닝 버튼
if st.sidebar.button("🗑️ 기존 데이터 초기화"):
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
        st.rerun()

# 사이드바 설정
st.sidebar.header("📂 과거 기록 보관소")
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    available_dates = sorted(hist_df['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("📅 날짜 선택", ["선택 안 함"] + available_dates)
else:
    selected_date = "선택 안 함"

# 1. 과거 기록 섹션 (생략 가능)

# 2. 실시간 전광판
st.subheader("📊 실시간 전종목 전광판")
if st.button("🔥 스캔 시작"):
    sample_tickers = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "GAUZ", "SLNH", "005930"]
    df_real = run_realtime_scan(sample_tickers)
    df_real.to_pickle(SAVE_FILE)
    st.rerun()

if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # [핵심 수정] 데이터 로드 후 열 존재 여부 체크 (에러 방어)
    required_cols = ['반등점수', '추세점수', 'Price', 'TOSS']
    for col in required_cols:
        if col not in df.columns:
            st.error(f"⚠️ 데이터 파일이 구버전입니다. '🔥 스캔 시작'을 눌러 데이터를 갱신하세요.")
            st.stop() # 에러가 나기 전에 실행 중단

    realtime_cfg = {
        "Price": st.column_config.NumberColumn("Price", format="%.2f"),
        "TOSS": st.column_config.LinkColumn("TOSS", display_text="🔵")
    }
    
    t1, t2 = st.tabs(["Phoenix", "Alpha"])
    with t1:
        st.dataframe(df.sort_values("반등점수", ascending=False).head(20), column_config=realtime_cfg, hide_index=True)
    with t2:
        st.dataframe(df.sort_values("추세점수", ascending=False).head(20), column_config=realtime_cfg, hide_index=True)
    
    if st.button("💾 오늘의 상위 5종목 기록하기"):
        record_top_picks(df)
