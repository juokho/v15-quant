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
TOSS_LOGO_URL = "https://static.toss.im/assets/homepage/safety/icn-security-fill.png" # 토스 로고 이미지

# 2. 데이터 업데이트 및 스캔 함수
def run_realtime_scan(ticker_list):
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(ticker_list):
        try:
            # 한국 종목(숫자로만 구성)은 .KS, 나머지는 그대로 사용
            full_ticker = f"{t}.KS" if t.isdigit() or t in ["GAUZ", "SLNH"] else t
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
                'Price': round(float(last['Close']), 2),
                'RSI': round(float(last['RSI']), 2),
                'MFI': round(float(last['MFI']), 2),
                'Vol_Accel': round(float(last['Vol_Accel']), 2),
                'Avg_Range': round(float(last['Avg_Range']), 2),
                'Volume_USD': float(last['Close'] * last['Volume']),
                '반등점수': 100 - float(last['RSI']),
                '추세점수': float(last['MFI'] * last['Vol_Accel']),
                'TOSS': f"https://tossinvest.com/stocks/{t}" # 토스 링크 생성
            })
        except Exception as e:
            continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    status_text.empty()
    return pd.DataFrame(all_results)

# 3. 기록 저장 함수
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

# --- UI 레이아웃 시작 ---
st.title("🛡️ V15 PRO - 타임라인 & 토스 연동 시스템")

# 공통 컬럼 설정 (토스 로고 포함)
column_cfg = {
    "Ticker": st.column_config.TextColumn("종목"),
    "Price": st.column_config.NumberColumn("Price", format="%.2f"),
    "TOSS": st.column_config.LinkColumn(
        "TOSS", 
        display_text="📲", # 표 안에서 아이콘으로 표시
        help="클릭 시 토스증권 상세 페이지로 이동합니다."
    ),
    "수익률(%)": st.column_config.NumberColumn("수익률", format="%.2f%%")
}

# 사이드바 설정
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

# 메인 버튼
c1, c2 = st.columns(2)
with c1:
    if st.button("🔥 실시간 전종목 스캔 시작"):
        sample_list = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "GAUZ", "SLNH", "005930"]
        updated_df = run_realtime_scan(sample_list)
        updated_df.to_pickle(SAVE_FILE)
        st.rerun()

# --- 데이터 표시 구역 ---
if selected_date != "선택 안 함":
    st.subheader(f"📅 {selected_date} 전략 타임라인 성적표")
    target_picks = hist_df[hist_df['Date'] == selected_date].copy()
    
    if st.button("📈 1일/3일/7일 수익률 분석하기"):
        with st.spinner("과거 데이터를 분석 중입니다..."):
            results = []
            base_date = datetime.strptime(selected_date, "%Y-%m-%d")
            
            for _, row in target_picks.iterrows():
                ticker = row['Ticker']
                buy_price = float(row['Buy_Price'])
                end_date = (base_date + timedelta(days=15)).strftime("%Y-%m-%d")
                df_history = yf.download(ticker, start=selected_date, end=end_date, progress=False)
                
                if not df_history.empty:
                    prices = df_history['Close'].tolist()
                    p1 = prices[1] if len(prices) > 1 else None
                    p3 = prices[3] if len(prices) > 3 else None
                    p7 = prices[7] if len(prices) > 7 else None
                    
                    def calc_return(p, b):
                        return round(((p - b) / b * 100), 2) if p else "대기중"

                    results.append({
                        'Strategy': row['Strategy'],
                        'Ticker': ticker,
                        'Buy_Price': buy_price,
                        '1일 후': calc_return(p1, buy_price),
                        '3일 후': calc_return(p3, buy_price),
                        '7일 후': calc_return(p7, buy_price),
                        'TOSS': f"https://tossinvest.com/stocks/{ticker}"
                    })
            
            st.dataframe(pd.DataFrame(results), column_config=column_cfg, hide_index=True)
    else:
        # 토스 링크 추가하여 표시
        target_picks['TOSS'] = target_picks['Ticker'].apply(lambda x: f"https://tossinvest.com/stocks/{x}")
        st.dataframe(target_picks, column_config=column_cfg, hide_index=True)
    st.markdown("---")

st.subheader("📊 오늘의 실시간 전광판")
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    f_df = df[(df['Volume_USD'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔵 Phoenix (반등)", "🟣 Alpha (추세)"])
    with t1:
        st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(50), column_config=column_cfg, hide_index=True, use_container_width=True)
    with t2:
        st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(50), column_config=column_cfg, hide_index=True, use_container_width=True)
    
    if st.button("💾 이 리스트를 오늘의 TOP으로 저장"):
        record_to_history(df)
else:
    st.info("스캔 시작 버튼을 눌러 데이터를 생성하세요.")
