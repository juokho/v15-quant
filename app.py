import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime

# 1. 기본 설정 및 폰트 스타일링
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

# [폰트 설정] 가독성 좋은 Pretendard 폰트 적용
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');

    /* 전체 폰트 적용 */
    * {
        font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, Roboto, sans-serif !important;
    }

    /* 제목 강조 */
    h1 {
        font-weight: 800 !important;
        letter-spacing: -1px;
        color: #FFFFFF;
    }

    /* 표 가독성 및 디자인 */
    .stDataFrame {
        border: 1px solid #31333F;
        border-radius: 8px;
    }
    
    /* 버튼 폰트 및 스타일 */
    .stButton>button {
        font-weight: 600 !important;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"
FOCUS_TICKERS = ["GAUZ", "SLNH"] 

# 2. 데이터 업데이트 및 스캔 함수 (V1 로직 유지)
def run_realtime_scan(ticker_list):
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(ticker_list):
        try:
            full_ticker = f"{t}.KS" if t in ["005930", "GAUZ", "SLNH"] else t
            status_text.text(f"🔍 스캔 중: {full_ticker} ({i+1}/{len(ticker_list)})")
            
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
        except Exception as e:
            continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    status_text.empty()
    return pd.DataFrame(all_results)

# 3. 기록 저장 함수 (V1 로직 유지)
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
    st.toast(f"✅ {today} 상위 종목 기록 완료!")

# --- UI 레이아웃 (V1 유지) ---
st.title("🛡️ V15 PRO - 전광판 & 백테스트 통합 시스템")

st.sidebar.header("🎛️ 오늘의 전광판 필터")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("최소 거래 가속도", 0.5, 5.0, 1.0)

st.sidebar.markdown("---")
st.sidebar.header("📂 과거 기록 보관소")
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    available_dates = sorted(hist_df['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("📅 날짜 선택", ["선택 안 함"] + available_dates)
else:
    selected_date = "선택 안 함"

if st.button("🔥 실시간 전종목 스캔 시작"):
    sample_list = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "GAUZ", "SLNH", "005930"]
    updated_df = run_realtime_scan(sample_list)
    updated_df.to_pickle(SAVE_FILE)
    st.rerun()

if selected_date != "선택 안 함":
    st.subheader(f"📅 {selected_date} 기록 및 수익률 추적")
    target_picks = hist_df[hist_df['Date'] == selected_date].copy()
    
    if st.button("📈 현재 수익률 계산하기"):
        with st.spinner("조회 중..."):
            current_prices = {}
            for t in target_picks['Ticker'].unique():
                try:
                    curr = yf.download(t, period="1d", progress=False)['Close'].iloc[-1]
                    current_prices[t] = curr
                except: current_prices[t] = 0
            
            target_picks['현재가'] = target_picks['Ticker'].map(current_prices)
            target_picks['수익률(%)'] = ((target_picks['현재가'] - target_picks['Buy_Price']) / target_picks['Buy_Price'] * 100).round(2)
            st.table(target_picks[['Strategy', 'Ticker', 'Buy_Price', '현재가', '수익률(%)']])
    else:
        st.table(target_picks)
    st.markdown("---")

st.subheader("📊 오늘의 실시간 전광판")
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    f_df = df[(df['Volume_USD'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔵 Phoenix (반등)", "🟣 Alpha (추세)"])
    with t1:
        st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(50), use_container_width=True)
    with t2:
        st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(50), use_container_width=True)
    
    if st.button("💾 이 리스트를 오늘의 TOP으로 저장"):
        record_to_history(df)
else:
    st.info("💡 스캔 시작 버튼을 눌러주세요.")
