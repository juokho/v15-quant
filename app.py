import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")
SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"
FOCUS_TICKERS = ["GAUZ", "SLNH"] # 사용자 집중 관리 종목 (티커만 입력)

# 2. 데이터 업데이트 및 스캔 함수 (내재화)
def run_realtime_scan(ticker_list):
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(ticker_list):
        try:
            # 한국/미국 티커 구분 처리 (단순화)
            full_ticker = f"{t}.KS" if t in ["005930", "GAUZ", "SLNH"] else t # 필요시 로직 확장
            status_text.text(f"🔍 스캔 중: {full_ticker} ({i+1}/{len(ticker_list)})")
            
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if len(df) < 20: continue

            # 지표 계산
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            
            # V15 핵심 지표 (가상 예시)
            avg_vol = df['Volume'].rolling(20).mean()
            df['Vol_Accel'] = df['Volume'] / avg_vol
            df['Avg_Range'] = (abs(df['High'] - df['Low']) / df['Close'] * 100).rolling(20).mean()
            
            # 점수 계산 (사용자 전략 반영)
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t,
                'Price': round(last['Close'], 2),
                'RSI': round(last['RSI'], 2),
                'MFI': round(last['MFI'], 2),
                'Vol_Accel': round(last['Vol_Accel'], 2),
                'Avg_Range': round(last['Avg_Range'], 2),
                'Volume_USD': last['Close'] * last['Volume'], # 대략적 거래대금
                '반등점수': 100 - last['RSI'], # 예시 로직
                '추세점수': last['MFI'] * last['Vol_Accel'] # 예시 로직
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
    
    # Phoenix/Alpha 상위 5개씩 추출
    p_top5 = df.sort_values(by="반등점수", ascending=False).head(5)
    a_top5 = df.sort_values(by="추세점수", ascending=False).head(5)
    
    for _, row in p_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': 'Phoenix', 'Ticker': row['Ticker'], 'Buy_Price': row['Price']})
    for _, row in a_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': 'Alpha', 'Ticker': row['Ticker'], 'Buy_Price': row['Price']})
    
    new_df = pd.DataFrame(new_records)
    if os.path.exists(TRACKER_FILE):
        old_df = pd.read_csv(TRACKER_FILE)
        # 오늘 이미 기록했다면 삭제 후 업데이트
        old_df = old_df[old_df['Date'] != today]
        final_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        final_df = new_df
    
    final_df.to_csv(TRACKER_FILE, index=False)
    st.toast(f"✅ {today} 상위 종목 기록 완료!")

# --- UI 레이아웃 시작 ---
st.title("🛡️ V15 PRO - 전광판 & 백테스트 통합 시스템")

# 사이드바 1: 필터 설정
st.sidebar.header("🎛️ 오늘의 전광판 필터")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("최소 거래 가속도", 0.5, 5.0, 1.0)

# 사이드바 2: 과거 기록 보관소 (블로그 탭 스타일)
st.sidebar.markdown("---")
st.sidebar.header("📂 과거 기록 보관소")
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    available_dates = sorted(hist_df['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("📅 날짜 선택", ["선택 안 함"] + available_dates)
else:
    selected_date = "선택 안 함"

# 메인 기능 버튼
c1, c2 = st.columns(2)
with c1:
    if st.button("🔥 실시간 전종목 스캔 시작"):
        # 실제로는 전종목 리스트를 넣으세요. 우선은 예시 티커들입니다.
        sample_list = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "GAUZ", "SLNH", "005930"]
        updated_df = run_realtime_scan(sample_list)
        updated_df.to_pickle(SAVE_FILE)
        st.rerun()

# --- 데이터 표시 구역 ---
if selected_date != "선택 안 함":
    # 탭 메뉴처럼 과거 기록을 상단에 노출
    st.subheader(f"📅 {selected_date} 기록 및 수익률 추적")
    target_picks = hist_df[hist_df['Date'] == selected_date].copy()
    
    if st.button("📈 현재 수익률 계산하기"):
        with st.spinner("실시간 가격 조회 중..."):
            current_prices = {}
            for t in target_picks['Ticker'].unique():
                try:
                    # 과거 기록 티커에 맞춰 처리 필요 (미국주식 기준 예시)
                    curr = yf.download(t, period="1d", progress=False)['Close'].iloc[-1]
                    current_prices[t] = curr
                except: current_prices[t] = 0
            
            target_picks['Price'] = target_picks['Ticker'].map(current_prices)
            target_picks['수익률(%)'] = ((target_picks['Price'] - target_picks['Buy_Price']) / target_picks['Buy_Price'] * 100).round(2)
            st.table(target_picks[['Strategy', 'Ticker', 'Buy_Price', 'Price', '수익률(%)']])
    else:
        st.table(target_picks)
    st.markdown("---")

# 오늘의 전광판 (필터 적용 결과)
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
    st.info("스캔 시작 버튼을 눌러 데이터를 생성하세요.")
