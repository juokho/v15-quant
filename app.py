import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor

# -----------------------------
# 기본 설정
# -----------------------------
st.set_page_config(page_title="V15 PRO QUANT V4", layout="wide")

if not os.path.exists("backdata"):
    os.makedirs("backdata")

LIVE_FILE = "v15_live.pkl"

# -----------------------------
# 캐시 함수
# -----------------------------

@st.cache_data(ttl=86400)
def get_nasdaq_list():
    df = fdr.StockListing('NASDAQ')
    return df['Symbol'].tolist()


@st.cache_data(ttl=3600)
def load_full_data(ticker, start, end):
    try:
        df = fdr.DataReader(ticker, start=start, end=end)
        if len(df) < 30:
            return None
        return df
    except:
        return None


# -----------------------------
# 분석 엔진 (슬라이싱 기반)
# -----------------------------

def analyze_from_full_df(t, df_full, target_date):

    df = df_full[df_full.index <= target_date].tail(60)

    if len(df) < 30:
        return None

    df['RSI'] = ta.rsi(df['Close'], length=14)
    df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
    df['Vol_Accel'] = df['Volume'] / df['Volume'].rolling(20).mean()

    last = df.iloc[-1]

    if pd.isna(last['RSI']) or pd.isna(last['MFI']) or pd.isna(last['Vol_Accel']):
        return None

    avg_price = (last['High'] + last['Low'] + last['Close']) / 3

    return {
        'Ticker': t,
        'Price_Val': float(last['Close']),
        '거래대금_Val': int(avg_price * last['Volume']),
        'Vol_Accel': float(last['Vol_Accel']),
        '반등점수': round(100 - float(last['RSI']), 1),
        '추세점수': round(float(last['MFI'] * last['Vol_Accel']), 1),
        'Toss': f"https://toss.im/stock-info/S/{t.upper()}"
    }


# -----------------------------
# V4 초고속 스캔 엔진
# -----------------------------

def run_fast_scan(target_date=None):

    is_live = target_date is None

    if is_live:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=90)
        save_path = LIVE_FILE
    else:
        end_date = target_date
        start_date = target_date - timedelta(days=90)
        save_path = f"backdata/v15_{target_date.strftime('%Y-%m-%d')}.pkl"

    tickers = get_nasdaq_list()

    full_data_dict = {}

    # 🔥 종목당 1회 다운로드
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(load_full_data, t, start_date, end_date): t
            for t in tickers
        }

        for future in futures:
            t = futures[future]
            df_full = future.result()
            if df_full is not None:
                full_data_dict[t] = df_full

    # 🔥 로컬 계산 (API 추가 호출 없음)
    results = []

    for t, df_full in full_data_dict.items():
        res = analyze_from_full_df(t, df_full, end_date)
        if res:
            results.append(res)

    if results:
        res_df = pd.DataFrame(results)
        res_df.to_pickle(save_path)
        return res_df

    return None


# -----------------------------
# 리더보드 출력
# -----------------------------

def display_board(df, score_col):

    d_df = df.copy()
    d_df['Price'] = d_df['Price_Val'].apply(lambda x: f"${x:,.2f}")
    d_df['거래대금'] = d_df['거래대금_Val'].apply(lambda x: f"${x:,}")
    d_df = d_df.sort_values(score_col, ascending=False).head(100)

    cols = ['Ticker', 'Price', '거래대금', 'Vol_Accel', score_col, 'Toss']

    st.dataframe(
        d_df[cols],
        use_container_width=True,
        hide_index=True,
        column_config={
            "Toss": st.column_config.LinkColumn("Toss", display_text="🚀")
        }
    )


# -----------------------------
# UI
# -----------------------------

st.sidebar.title("💎 V15 PRO V4")
app_mode = st.sidebar.selectbox("메뉴 선택", ["📊 실시간/과거 조회", "📥 데이터 수집기"])

st.sidebar.markdown("---")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_acc = st.sidebar.slider("거래가속 필터", 0.5, 5.0, 1.2)

# -----------------------------
# 조회 모드
# -----------------------------

if app_mode == "📊 실시간/과거 조회":

    st.subheader("🏁 리더보드 조회")

    tab_live, tab_hist = st.tabs(["🟢 실시간", "🕒 과거 백데이터"])

    # -------------------------
    # 실시간
    # -------------------------

    with tab_live:

        if st.button("🚀 실시간 초고속 스캔"):
            run_fast_scan(None)
            st.rerun()

        if os.path.exists(LIVE_FILE):

            df = pd.read_pickle(LIVE_FILE)

            f_df = df[
                (df['거래대금_Val'] >= min_val) &
                (df['Vol_Accel'] >= min_acc)
            ]

            t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])

            with t1:
                display_board(f_df, '반등점수')

            with t2:
                display_board(f_df, '추세점수')

    # -------------------------
    # 과거 조회
    # -------------------------

    with tab_hist:

        sel_date = st.date_input("날짜 선택", value=datetime.now() - timedelta(days=1))
        path = f"backdata/v15_{sel_date.strftime('%Y-%m-%d')}.pkl"

        if os.path.exists(path):

            df_hist = pd.read_pickle(path)

            f_df_h = df_hist[
                (df_hist['거래대금_Val'] >= min_val) &
                (df_hist['Vol_Accel'] >= min_acc)
            ]

            t1, t2 = st.tabs(["🔵 과거 바닥반등", "🟣 과거 상승추세"])

            with t1:
                display_board(f_df_h, '반등점수')

            with t2:
                display_board(f_df_h, '추세점수')

        else:
            st.warning("선택한 날짜의 데이터가 없습니다. 데이터 수집기에서 먼저 수집하세요.")


# -----------------------------
# 백데이터 수집기
# -----------------------------

else:

    st.subheader("📥 V4 백데이터 수집 엔진")

    c_start = st.date_input("시작 날짜", value=datetime(2026, 2, 1))
    c_end = st.date_input("종료 날짜", value=datetime.now())

    if st.button("🚀 기간 전체 초고속 수집 시작"):

        curr = c_start
        progress_bar = st.progress(0)

        date_list = []

        while curr <= c_end:
            if curr.weekday() < 5:
                date_list.append(curr)
            curr += timedelta(days=1)

        for i, d in enumerate(date_list):

            run_fast_scan(d)
            progress_bar.progress((i + 1) / len(date_list))

        st.success("✅ 선택한 기간의 데이터 수집 완료!")
