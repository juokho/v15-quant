import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
import time
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# 1. 기본 설정 및 폴더 생성
st.set_page_config(page_title="V15 PRO QUANT V3.13", layout="wide")

if not os.path.exists("backdata"):
    os.makedirs("backdata")

LIVE_FILE = "v15_live.pkl"

# [엔진] 단일 종목 분석 (최속화)
def analyze_ticker(t, date_str, is_live):
    try:
        # 특정 종목 지침 준수 (제외)
        if t in ['SLNH', 'GAUZ']: return None
        
        df = fdr.DataReader(t, end=date_str).tail(60) if not is_live else fdr.DataReader(t).tail(60)
        if len(df) < 30: return None
        
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
        df.loc[:, 'Vol_Accel'] = df['Volume'] / df['Volume'].rolling(20).mean()
        
        last = df.iloc[-1]
        return {
            'Ticker': t, 'Price_Val': float(last['Close']),
            '거래대금_Val': int(last['Close'] * last['Volume']),
            'Vol_Accel': float(last['Vol_Accel']),
            '반등점수': round(100 - float(last['RSI']), 1),
            '추세점수': round(float(last['MFI'] * last['Vol_Accel']), 1),
            'Toss': f"https://toss.im/stock-info/S/{t.upper()}"
        }
    except: return None

# [엔진] 스캔 함수
def run_fast_scan(target_date=None):
    is_live = target_date is None
    date_str = datetime.now().strftime('%Y-%m-%d') if is_live else target_date.strftime('%Y-%m-%d')
    save_path = LIVE_FILE if is_live else f"backdata/v15_{date_str}.pkl"
    
    try:
        df_nasdaq = fdr.StockListing('NASDAQ')
        tickers = df_nasdaq['Symbol'].tolist()
        
        results = []
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(analyze_ticker, t, date_str, is_live) for t in tickers]
            for future in futures:
                res = future.result()
                if res: results.append(res)
        
        res_df = pd.DataFrame(results)
        if not res_df.empty:
            res_df.to_pickle(save_path)
            return res_df
    except: pass
    return None

# [출력] 리더보드 포맷팅 (V3 지침)
def display_board(df, score_col):
    d_df = df.copy()
    d_df['Price'] = d_df['Price_Val'].apply(lambda x: f"${x:,.2f}")
    d_df['거래대금'] = d_df['거래대금_Val'].apply(lambda x: f"${x:,}")
    d_df = d_df.sort_values(score_col, ascending=False).head(100)
    
    cols = ['Ticker', 'Price', '거래대금', 'Vol_Accel', score_col, 'Toss']
    st.dataframe(d_df[cols], use_container_width=True, hide_index=True,
                 column_config={"Toss": st.column_config.LinkColumn("Toss", display_text="🚀")})

# --- UI 메인 ---
# 사이드바에서 모드를 완전히 분리하여 수집과 조회가 엉키지 않게 함
st.sidebar.title("💎 V15 PRO V3.13")
app_mode = st.sidebar.selectbox("메뉴 선택", ["📊 실시간/과거 조회", "📥 데이터 수집기"])

# 필터링은 항상 노출
st.sidebar.markdown("---")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_acc = st.sidebar.slider("거래가속 필터", 0.5, 5.0, 1.2)

if app_mode == "📊 실시간/과거 조회":
    st.subheader("🏁 리더보드 조회")
    tab_live, tab_hist = st.tabs(["🟢 실시간", "🕒 과거 백데이터"])
    
    with tab_live:
        if st.button("🚀 실시간 고속 스캔"):
            run_fast_scan(None)
            st.rerun()
        if os.path.exists(LIVE_FILE):
            df = pd.read_pickle(LIVE_FILE)
            f_df = df[(df['거래대금_Val'] >= min_val) & (df['Vol_Accel'] >= min_acc)]
            t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
            with t1: display_board(f_df, '반등점수')
            with t2: display_board(f_df, '추세점수')
            
    with tab_hist:
        sel_date = st.date_input("날짜 선택", value=datetime.now() - timedelta(days=1))
        path = f"backdata/v15_{sel_date.strftime('%Y-%m-%d')}.pkl"
        if os.path.exists(path):
            df_hist = pd.read_pickle(path)
            f_df_h = df_hist[(df_hist['거래대금_Val'] >= min_val) & (df_hist['Vol_Accel'] >= min_acc)]
            t1, t2 = st.tabs(["🔵 과거 바닥반등", "🟣 과거 상승추세"])
            with t1: display_board(f_df_h, '반등점수')
            with t2: display_board(f_df_h, '추세점수')
        else:
            st.warning("선택한 날짜의 데이터가 없습니다. '데이터 수집기' 메뉴에서 먼저 수집하세요.")

else: # 데이터 수집기 모드
    st.subheader("📥 백데이터 일괄 수집 엔진")
    st.info("여기서 수집을 시작하면 날짜별로 파일이 저장됩니다. 수집 중에도 메뉴를 바꿔 조회가 가능합니다.")
    
    c_start = st.date_input("시작 날짜", value=datetime(2026, 2, 1))
    c_end = st.date_input("종료 날짜", value=datetime.now())
    
    if st.button("🚀 2월 전체 고속 수집 시작"):
        curr = c_start
        status_area = st.empty()
        progress_bar = st.progress(0)
        
        # 전체 날짜 계산
        date_list = []
        while curr <= c_end:
            if curr.weekday() < 5: date_list.append(curr)
            curr += timedelta(days=1)
            
        for i, d in enumerate(date_list):
            d_str = d.strftime('%Y-%m-%d')
            status_area.write(f"🔥 현재 수집 중: **{d_str}** ({i+1}/{len(date_list)})")
            run_fast_scan(d)
            progress_bar.progress((i + 1) / len(date_list))
            
        st.success("✅ 선택한 기간의 모든 데이터 수집이 완료되었습니다!")
