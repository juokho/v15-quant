import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed

# -----------------------------
# 1. 기본 설정 및 폴더 구성
# -----------------------------
st.set_page_config(page_title="V15 PRO QUANT V3.14", layout="wide")

if not os.path.exists("backdata"):
    os.makedirs("backdata")

LIVE_FILE = "v15_live.pkl"

# -----------------------------
# 2. 캐시 및 데이터 로드 최적화
# -----------------------------
@st.cache_data(ttl=86400)
def get_nasdaq_list():
    """종목 리스트를 하루 한 번만 가져옵니다. 제한 종목은 여기서 원천 차단됩니다."""
    df = fdr.StockListing('NASDAQ')
    tickers = df['Symbol'].tolist()
    # 지침 준수: 특정 종목 사전 차단 (명시 금지 조항 적용)
    return [t for t in tickers if t not in ['SLNH', 'GAUZ']]

# -----------------------------
# 3. 분석 엔진 (슬라이싱 기반 초고속 연산)
# -----------------------------
def analyze_slice(t, df_full, target_date):
    """미리 다운받은 전체 데이터(df_full)에서 특정 날짜까지만 잘라서 분석합니다."""
    date_str = target_date.strftime('%Y-%m-%d')
    df = df_full[df_full.index <= date_str].tail(60).copy()
    
    if len(df) < 30: return None

    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
    df['Vol_Accel'] = df['Volume'] / df['Volume'].rolling(20).mean()

    last = df.iloc[-1]
    
    if pd.isna(last['RSI']) or pd.isna(last['MFI']): return None

    return {
        'Ticker': t,
        'Price_Val': float(last['Close']), # 지침: "현재가" should be "Price"
        '거래대금_Val': int(last['Close'] * last['Volume']),
        'Vol_Accel': float(last['Vol_Accel']),
        '반등점수': round(100 - float(last['RSI']), 1),
        '추세점수': round(float(last['MFI'] * last['Vol_Accel']), 1),
        'Toss': f"https://toss.im/stock-info/S/{t.upper()}"
    }

# -----------------------------
# 4. 수익률 자동 계산 엔진 (복구됨)
# -----------------------------
def calculate_historical_returns(df):
    """과거 리더보드의 Price와 오늘 실시간 시세를 대조하여 수익률을 매깁니다."""
    returns = []
    with st.spinner("📈 최신 시세를 불러와 수익률을 계산 중입니다..."):
        # 상위 100개만 제한적으로 불러와 속도 저하 방지
        for _, row in df.iterrows():
            try:
                curr_data = fdr.DataReader(row['Ticker']).iloc[-1]
                curr_price = float(curr_data['Close'])
                buy_price = row['Price_Val']
                gain = ((curr_price - buy_price) / buy_price) * 100
                returns.append({'Current_Price': curr_price, 'Return_Pct': round(gain, 2)})
            except:
                returns.append({'Current_Price': 0.0, 'Return_Pct': 0.0})
                
    ret_df = pd.DataFrame(returns)
    return pd.concat([df.reset_index(drop=True), ret_df], axis=1)

# -----------------------------
# 5. 스캔 함수 (실시간 & 일괄 수집 통합)
# -----------------------------
def fetch_ticker_data(t, start, end):
    try:
        df = fdr.DataReader(t, start=start, end=end)
        return t, df if len(df) >= 30 else None
    except: return t, None

def run_batch_scan(start_date, end_date, is_live=False):
    """일괄 수집의 핵심: API는 종목당 딱 1번만 호출하고 메모리에서 모든 날짜를 계산합니다."""
    tickers = get_nasdaq_list()
    
    # 분석할 날짜 리스트 생성
    date_list = []
    if is_live:
        date_list = [datetime.now()]
    else:
        curr = start_date
        while curr <= end_date:
            if curr.weekday() < 5: date_list.append(curr)
            curr += timedelta(days=1)

    # 날짜별 결과를 담을 딕셔너리
    results_by_date = {d: [] for d in date_list}
    fetch_start = (start_date - timedelta(days=90)).strftime('%Y-%m-%d')
    fetch_end = datetime.now().strftime('%Y-%m-%d') if is_live else end_date.strftime('%Y-%m-%d')

    progress_bar = st.progress(0)
    status_text = st.empty()

    # 멀티스레딩으로 종목별 90일치 데이터를 단 1회씩만 다운로드
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(fetch_ticker_data, t, fetch_start, fetch_end) for t in tickers]
        
        for i, future in enumerate(as_completed(futures)):
            t, df_full = future.result()
            
            if df_full is not None:
                # 다운받은 1개의 DataFrame으로 모든 날짜에 대해 슬라이싱 분석 진행
                for target_date in date_list:
                    res = analyze_slice(t, df_full, target_date)
                    if res: results_by_date[target_date].append(res)
            
            if i % 50 == 0:
                progress_bar.progress((i + 1) / len(tickers))
                status_text.write(f"🚀 분석 진행 중... ({i+1}/{len(tickers)})")

    progress_bar.empty()
    status_text.empty()

    # 날짜별로 파일 분리 저장
    for target_date, results in results_by_date.items():
        if results:
            res_df = pd.DataFrame(results)
            save_path = LIVE_FILE if is_live else f"backdata/v15_{target_date.strftime('%Y-%m-%d')}.pkl"
            res_df.to_pickle(save_path)

# -----------------------------
# 6. 리더보드 출력 함수
# -----------------------------
def display_board(df, score_col, show_returns=False):
    d_df = df.copy()
    d_df['Price'] = d_df['Price_Val'].apply(lambda x: f"${x:,.2f}")
    d_df['거래대금'] = d_df['거래대금_Val'].apply(lambda x: f"${x:,}")
    
    d_df = d_df.sort_values(score_col, ascending=False).head(100)
    
    if show_returns and 'Return_Pct' in d_df.columns:
        d_df['최신시세'] = d_df['Current_Price'].apply(lambda x: f"${x:,.2f}")
        d_df['수익률'] = d_df['Return_Pct'].apply(lambda x: f"{x:+.2f}%")
        cols = ['Ticker', 'Price', '최신시세', '수익률', '거래대금', score_col, 'Toss']
    else:
        cols = ['Ticker', 'Price', '거래대금', 'Vol_Accel', score_col, 'Toss']
        
    actual_cols = [c for c in cols if c in d_df.columns]
    
    st.dataframe(d_df[actual_cols], use_container_width=True, hide_index=True,
                 column_config={"Toss": st.column_config.LinkColumn("Toss", display_text="🚀")})

# -----------------------------
# 7. UI 구성 (조회 / 수집 분리)
# -----------------------------
st.sidebar.title("💎 V15 PRO V3.14")
app_mode = st.sidebar.selectbox("메뉴 선택", ["📊 실시간/과거 조회", "📥 데이터 수집기"])
st.sidebar.markdown("---")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_acc = st.sidebar.slider("거래가속 필터", 0.5, 5.0, 1.2)

if app_mode == "📊 실시간/과거 조회":
    st.subheader("🏁 리더보드 및 수익률 조회")
    tab_live, tab_hist = st.tabs(["🟢 실시간", "🕒 과거 백데이터 및 수익률"])
    
    with tab_live:
        if st.button("🚀 실시간 고속 스캔"):
            run_batch_scan(datetime.now(), datetime.now(), is_live=True)
            st.rerun()
            
        if os.path.exists(LIVE_FILE):
            df = pd.read_pickle(LIVE_FILE)
            f_df = df[(df['거래대금_Val'] >= min_val) & (df['Vol_Accel'] >= min_acc)]
            t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
            with t1: display_board(f_df, '반등점수')
            with t2: display_board(f_df, '추세점수')

    with tab_hist:
        col1, col2 = st.columns([1, 1])
        with col1:
            sel_date = st.date_input("조회할 과거 날짜", value=datetime.now() - timedelta(days=1))
        
        path = f"backdata/v15_{sel_date.strftime('%Y-%m-%d')}.pkl"
        
        if os.path.exists(path):
            df_hist = pd.read_pickle(path)
            
            with col2:
                # 부활한 수익률 자동 계산 버튼
                if st.button("📈 이 날짜 종목들의 현재 수익률 계산"):
                    df_with_returns = calculate_historical_returns(df_hist)
                    df_with_returns.to_pickle(path) # 수익률 계산 결과 덮어쓰기
                    st.rerun()

            f_df_h = df_hist[(df_hist['거래대금_Val'] >= min_val) & (df_hist['Vol_Accel'] >= min_acc)]
            has_returns = 'Return_Pct' in f_df_h.columns
            
            t1, t2 = st.tabs(["🔵 과거 바닥반등 결과", "🟣 과거 상승추세 결과"])
            with t1: display_board(f_df_h, '반등점수', show_returns=has_returns)
            with t2: display_board(f_df_h, '추세점수', show_returns=has_returns)
        else:
            st.warning("선택한 날짜의 데이터가 없습니다. [데이터 수집기] 메뉴에서 수집을 진행해 주세요.")

else: # 데이터 수집기
    st.subheader("📥 백데이터 Batch 수집 엔진 (API 1회 호출 최적화)")
    st.info("💡 종목별 데이터를 한 번만 다운로드하여 설정된 기간의 모든 날짜를 초고속으로 동시 분석합니다.")
    
    c_start = st.date_input("시작 날짜", value=datetime(2026, 2, 1))
    c_end = st.date_input("종료 날짜", value=datetime.now())
    
    if st.button("🚀 기간 전체 Batch 고속 수집 시작"):
        run_batch_scan(c_start, c_end, is_live=False)
        st.success("✅ 선택한 기간의 백데이터 수집이 완료되었습니다! 조회 메뉴로 이동하세요.")
