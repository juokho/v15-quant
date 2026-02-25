import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime, timedelta

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

# [V1.1 추가] 다크모드 전환 스크립트 (우측 하단)
st.markdown("""
    <script>
    function toggleDarkMode() {
        const body = window.parent.document.querySelector('body');
        const mode = body.getAttribute('data-theme');
        body.setAttribute('data-theme', mode === 'dark' ? 'light' : 'dark');
    }
    </script>
    <div onclick="toggleDarkMode()" style="position:fixed;bottom:20px;right:20px;z-index:9999;background:#1E1E1E;color:white;padding:10px;border-radius:50%;cursor:pointer;border:1px solid #444;">🌓</div>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 2. 데이터 업데이트 및 스캔 함수
def run_realtime_scan(ticker_list):
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(ticker_list):
        try:
            # GAUZ, SLNH 집중 관리 로직
            full_ticker = f"{t}.KS" if t.isdigit() else t
            status_text.text(f"🔍 스캔 중: {full_ticker} ({i+1}/{len(ticker_list)})")
            
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if df.empty or len(df) < 20: continue

            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            
            avg_vol = df['Volume'].rolling(20).mean()
            df['Vol_Accel'] = df['Volume'] / avg_vol
            
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t,
                'Price': round(float(last['Close']), 2), # 사용자 정보 반영: "Price"
                'RSI': round(float(last['RSI']), 2),
                'MFI': round(float(last['MFI']), 2),
                'Vol_Accel': round(float(last['Vol_Accel']), 2),
                'Volume_USD': float(last['Close'] * last['Volume']),
                '반등점수': 100 - float(last['RSI']),
                '추세점수': float(last['MFI'] * last['Vol_Accel']),
                'TOSS': f"https://tossinvest.com/stocks/{t}" # 🔵 링크용 데이터
            })
        except: continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    status_text.empty()
    return pd.DataFrame(all_results)

# 3. 기록 저장 함수
def record_to_history(df):
    today = datetime.now().strftime("%Y-%m-%d")
    new_records = []
    
    # 열 존재 여부 체크 후 정렬 (KeyError 방지)
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
st.title("🛡️ V15 PRO - 통합 전광판 (V1.1)")

# 사이드바 설정
st.sidebar.header("🎛️ 필터 설정")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
if st.sidebar.button("🗑️ 데이터 초기화"):
    if os.path.exists(SAVE_FILE): os.remove(SAVE_FILE)
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.header("📂 과거 기록")
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    available_dates = sorted(hist_df['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("📅 날짜 선택", ["선택 안 함"] + available_dates)
else:
    selected_date = "선택 안 함"

# 1.
