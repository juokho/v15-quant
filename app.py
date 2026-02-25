import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
import time
from datetime import datetime

# 1. 기본 설정 및 폰트 (아이콘 깨짐 방지 포함)
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    html, body, [class*="css"] { font-family: 'Pretendard' !important; }
    .st-emotion-cache-17l6l7d, .material-icons, [data-testid="stSidebarCollapseButton"] span {
        font-family: 'Material Icons' !important;
    }
    h1 { font-weight: 800 !important; letter-spacing: -1px; }
    </style>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 2. 내재화된 전체 시장 스캔 함수
def run_full_market_scan():
    all_results = []
    with st.spinner("📡 나스닥(NASDAQ) 전체 리스트 확보 중..."):
        try:
            df_nasdaq = fdr.StockListing('NASDAQ')
            # 집중 관리 종목 제외 (GAUZ, SLNH)
            exclude = ['GAUZ', 'SLNH']
            tickers = [t for t in df_nasdaq['Symbol'].tolist() if t not in exclude]
        except Exception as e:
            st.error(f"리스트 확보 실패: {e}")
            return pd.DataFrame()

    total_count = len(tickers)
    progress_bar = st.progress(0)
    status_text = st.empty()
    
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
                'Price': round(float(last['Close']), 2), # "현재가" 대신 "Price"
                'RSI': round(float(last['RSI']), 2) if not pd.isna(last['RSI']) else 50,
                'MFI': round(float(last['MFI']), 2) if not pd.isna(last['MFI']) else 50,
                'Vol_Accel': round(float(last['Vol_Accel']), 2) if not pd.isna(last['Vol_Accel']) else 1,
                'Volume_USD': float(last['Close'] * last['Volume']),
                '반등점수': 100 - float(last['RSI']),
                '추세점수': float(last['MFI'] * last['Vol_Accel'])
            })
            if i % 20 == 0:
                status_text.text(f"📦 분석 중: {t} ({i}/{total_count})")
                progress_bar.progress((i + 1) / total_count)
            time.sleep(0.01)
        except: continue
            
    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(all_results)

# 3. 백테스트 기록 저장 함수
def record_to_history(df):
    today = datetime.now().strftime("%Y-%m-%d")
    new_records = []
    p_top5 = df.sort_values(by="반등점수", ascending=False).head(5)
    a_top5 = df.sort_values(by="추세점수", ascending=False).head(5)
    
    for _, row in p_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': '바닥반등', 'Ticker': row['Ticker'], 'Buy_Price': row['Price']})
    for _, row in a_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': '상승추세', 'Ticker': row['Ticker'], 'Buy_Price': row['Price']})
    
    new_df = pd.DataFrame(new_records)
    if os.path.exists(TRACKER_FILE):
        old_df = pd.read_csv(TRACKER_FILE)
        old_df = old_df[old_df['Date'] != today]
        final_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        final_df = new_df
    final_df.to_csv(TRACKER_FILE, index=False)
    st.toast(f"✅ {today} 상위 종목 기록 완료!")

# --- 메인 UI ---
st.title("💵 V15 PRO LEADER BOARD")

# 사이드바 필터
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

# 스캔 버튼
if st.button("🔥 나스닥 전체 실시간 스캔 시작 (내재화)"):
    start_time = time.time()
    updated_df = run_full_market_scan()
    if not updated_df.empty:
        updated_df.to_pickle(SAVE_FILE)
        st.success(f"✅ 스캔 완료! ({int(time.time() - start_time)}초)")
        st.rerun()

# 백테스트 구역
if selected_date != "선택 안 함":
    st.subheader(f"📅 {selected_date} Pick & 수익률 추적")
    target_picks = hist_df[hist_df['Date'] == selected_date].copy()
    
    if st.button("📈 실시간 수익률 확인"):
        with st.spinner("현재가 조회 중..."):
            for idx, row in target_picks.iterrows():
                try:
                    curr_price = fdr.DataReader(row['Ticker']).iloc[-1]['Close']
                    target_picks.at[idx, '현재가'] = round(curr_price, 2)
                except: target_picks.at[idx, '현재가'] = 0
            
            target_picks['수익률(%)'] = ((target_picks['현재가'] - target_picks['Buy_Price']) / target_picks['Buy_Price'] * 100).round(2)
            st.table(target_picks[['Strategy', 'Ticker', 'Buy_Price', '현재가', '수익률(%)']])
    else:
        st.table(target_picks)
    st.markdown("---")

# 실시간 성적표 표시
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    f_df = df[(df['Volume_USD'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
    with t1:
        st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(100), use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(100), use_container_width=True, hide_index=True)
    
    if st.button("💾 이 리스트를 오늘의 TOP으로 저장"):
        record_to_history(df)
else:
    st.info("💡 스캔 버튼을 눌러 성적표를 만듭니다.")
