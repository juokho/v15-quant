import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime

# 1. 기본 설정 및 힙한 폰트/스타일링 적용
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

# [구글 폰트 로드 & CSS 적용]
# 국문: 프리텐다드(가독성 끝판왕), 영문/숫자: 몬세라트(힙한 감성)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@700;800&family=Pretendard:wght@400;600&display=swap');

    /* 전체 기본 폰트 설정 */
    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }

    /* 타이틀 및 강조 폰트 */
    h1, h2, h3, .stButton>button {
        font-family: 'Montserrat', sans-serif !important;
        letter-spacing: -0.5px;
    }

    /* 사이드바 배경 및 텍스트 설정 */
    .css-1d391kg {
        background-color: #0E1117;
    }

    /* 테이블 가독성 강화 */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 15px rgba(0,0,0,0.3);
    }
    </style>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"
FOCUS_TICKERS = ["GAUZ", "SLNH"]

# 2. 데이터 업데이트 및 스캔 함수
def run_realtime_scan(ticker_list):
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(ticker_list):
        try:
            full_ticker = f"{t}.KS" if t in ["005930", "GAUZ", "SLNH"] else t
            status_text.text(f"📡 SCANNING: {full_ticker} ({i+1}/{len(ticker_list)})")
            
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if len(df) < 20: continue

            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            
            avg_vol = df['Volume'].rolling(20).mean()
            df['Vol_Accel'] = df['Volume'] / avg_vol
            df['Avg_Range'] = (abs(df['High'] - df['Low']) / df['Close'] * 100).rolling(20).mean()
            
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t,
                'Price': round(last['Close'], 2), # "현재가" 대신 "Price"
                'RSI': round(last['RSI'], 2),
                'MFI': round(last['MFI'], 2),
                'Vol_Accel': round(last['Vol_Accel'], 2),
                'Avg_Range': round(last['Avg_Range'], 2),
                'Volume_USD': last['Close'] * last['Volume'],
                '반등점수': 100 - last['RSI'],
                '추세점수': last['MFI'] * last['Vol_Accel']
            })
        except Exception:
            continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    status_text.empty()
    return pd.DataFrame(all_results)

def record_to_history(df):
    today = datetime.now().strftime("%Y-%m-%d")
    new_records = []
    p_top5 = df.sort_values(by="반등점수", ascending=False).head(5)
    a_top5 = df.sort_values(by="추세점수", ascending=False).head(5)
    
    for _, row in p_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': 'Phoenix', 'Ticker': row['Ticker'], 'Buy_Price': row['Price']})
    for _, row in a_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': 'Alpha', 'Ticker': row['Ticker'], 'Buy_Price': row['Price']})
    
    new_df = pd.DataFrame(new_records)
    if os.path.exists(TRACKER_FILE):
        old_df = pd.read_csv(TRACKER_FILE)
        old_df = old_df[old_df['Date'] != today]
        final_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        final_df = new_df
    final_df.to_csv(TRACKER_FILE, index=False)
    st.toast(f"✅ {today} ARCHIVED.")

# --- UI 레이아웃 ---
st.title("🛰️ V15 PRO QUANT TERMINAL") # 이모지 변경 가능

st.sidebar.header("🎛️ SYSTEM FILTER")
min_val = st.sidebar.number_input("MIN VOLUME ($)", value=1000000)
min_vol_acc = st.sidebar.slider("VOL ACCEL", 0.5, 5.0, 1.0)

st.sidebar.markdown("---")
st.sidebar.header("📂 ARCHIVE")
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    available_dates = sorted(hist_df['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("📅 SELECT DATE", ["NONE"] + available_dates)
else:
    selected_date = "NONE"

if st.button("🔥 RUN SYSTEM SCAN"):
    sample_list = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "GAUZ", "SLNH", "005930"]
    updated_df = run_realtime_scan(sample_list)
    updated_df.to_pickle(SAVE_FILE)
    st.rerun()

if selected_date != "NONE":
    st.subheader(f"📅 HISTORY: {selected_date}")
    target_picks = hist_df[hist_df['Date'] == selected_date].copy()
    st.table(target_picks)
    st.markdown("---")

st.subheader("📊 REAL-TIME LEADERBOARD")
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    f_df = df[(df['Volume_USD'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔹 PHOENIX (MEAN-REVERSION)", "🔸 ALPHA (TREND-FOLLOWING)"])
    with t1:
        st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(50), use_container_width=True)
    with t2:
        st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(50), use_container_width=True)
    
    if st.button("💾 SAVE TODAY'S TOP PICKS"):
        record_to_history(df)
else:
    st.info("💡 PRESS 'RUN SYSTEM SCAN' TO START.")
