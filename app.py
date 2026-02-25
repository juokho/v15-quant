import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
import time
from datetime import datetime, timedelta

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT V3.9", layout="wide")

LIVE_FILE = "v15_live.pkl"      # 오늘 자 실시간 데이터
HIST_FILE = "v15_history.pkl"   # 과거 타임머신 데이터
TRACKER_FILE = "portfolio_tracker.csv"

# 2. 스캔 함수 (Mode에 따라 파일 분리 저장)
def run_scan(target_date=None):
    all_results = []
    is_live = target_date is None
    date_str = datetime.now().strftime('%Y-%m-%d') if is_live else target_date.strftime('%Y-%m-%d')
    
    msg = "📡 실시간 나스닥 분석 중..." if is_live else f"📡 {date_str} 기준 데이터 복구 중..."
    with st.spinner(msg):
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
            # 타임머신일 경우 해당 날짜까지의 데이터만 가져옴
            df = fdr.DataReader(t, end=date_str).tail(60) if not is_live else fdr.DataReader(t).tail(60)
            if len(df) < 30: continue

            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            df['Vol_Accel'] = df['Volume'] / df['Volume'].rolling(20).mean()
            
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t,
                'Price_Val': float(last['Close']), # 당시 가격
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
    res_df = pd.DataFrame(all_results)
    if not res_df.empty:
        save_path = LIVE_FILE if is_live else HIST_FILE
        res_df.to_pickle(save_path)
    return res_df

# 3. 수익률 계산 함수 (과거 데이터용)
def calculate_returns(df):
    with st.spinner("📈 현재가 대조하여 수익률 계산 중..."):
        returns = []
        for _, row in df.iterrows():
            try:
                # 현재 시점의 최신가 한 줄 가져오기
                current_data = fdr.DataReader(row['Ticker']).iloc[-1]
                curr_price = float(current_data['Close'])
                gain = ((curr_price - row['Price_Val']) / row['Price_Val']) * 100
                returns.append({'Current_Price': curr_price, 'Return_Pct': round(gain, 2)})
            except:
                returns.append({'Current_Price': 0, 'Return_Pct': 0})
        
        return pd.concat([df.reset_index(drop=True), pd.DataFrame(returns)], axis=1)

# 4. 출력 함수
def display_board(df, score_col, is_history=False):
    if df.empty:
        st.warning("🧐 데이터가 없습니다.")
        return

    display_df = df.copy()
    display_df['Price'] = display_df['Price_Val'].apply(lambda x: f"${x:,.2f}")
    display_df['거래대금'] = display_df['거래대금_Val'].apply(lambda x: f"${x:,}")
    
    # 수익률이 계산된 경우 포맷팅
    if 'Return_Pct' in display_df.columns:
        display_df['수익률'] = display_df['Return_Pct'].apply(lambda x: f"{x:+.2f}%")
        display_df['현재가'] = display_df['Current_Price'].apply(lambda x: f"${x:,.2f}")
        cols = ['Ticker', 'Price', '현재가', '수익률', '거래대금', score_col, 'Toss']
    else:
        cols = ['Ticker', 'Price', '거래대금', 'Vol_Accel', score_col, 'Toss']
    
    actual_cols = [c for c in cols if c in display_df.columns]
    
    st.dataframe(
        display_df[actual_cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Toss": st.column_config.LinkColumn("Toss", display_text="🚀"),
            "수익률": st.column_config.TextColumn("수익률") # 색상 강조 등은 텍스트로 대체
        }
    )

# --- 메인 UI ---
st.title("💵 V15 PRO QUANT V3.9")

# 사이드바 모드 분리
mode = st.sidebar.radio("📡 모드 선택", ["실시간 스캔", "과거 수익률 분석"])

st.sidebar.markdown("---")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("평균 대비 거래량", 0.5, 5.0, 1.2)

if mode == "실시간 스캔":
    st.header("🟢 Live Market Leaderboard")
    if st.button("🔥 나스닥 실시간 스캔 시작"):
        run_scan(None)
        st.rerun()
    
    if os.path.exists(LIVE_FILE):
        df = pd.read_pickle(LIVE_FILE)
        f_df = df[(df['거래대금_Val'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
        t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
        with t1: display_board(f_df.sort_values('반등점수', ascending=False).head(100), '반등점수')
        with t2: display_board(f_df.sort_values('추세점수', ascending=False).head(100), '추세점수')

else:
    st.header("🕒 Historical Return Analysis")
    selected_date = st.date_input("분석할 과거 날짜", value=datetime.now() - timedelta(days=1))
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🕰️ 해당 날짜 데이터 스캔/복구"):
            run_scan(selected_date)
            st.rerun()
    
    if os.path.exists(HIST_FILE):
        df = pd.read_pickle(HIST_FILE)
        
        with col2:
            if st.button("📈 현재가 기준 수익률 계산"):
                df_with_returns = calculate_returns(df)
                df_with_returns.to_pickle(HIST_FILE) # 수익률 포함해서 갱신
                st.rerun()

        f_df = df[(df['거래대금_Val'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
        
        t1, t2 = st.tabs(["🔵 바닥반등 결과", "🟣 상승추세 결과"])
        with t1: display_board(f_df.sort_values('반등점수', ascending=False).head(100), '반등점수', True)
        with t2: display_board(f_df.sort_values('추세점수', ascending=False).head(100), '추세점수', True)
