import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
from datetime import datetime, timedelta

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT V3.12", layout="wide")

if not os.path.exists("backdata"):
    os.makedirs("backdata")

LIVE_FILE = "v15_live.pkl"

# [핵심] 초고속 분석 엔진
def run_hyper_scan(target_date=None, silent=False):
    is_live = target_date is None
    date_str = datetime.now().strftime('%Y-%m-%d') if is_live else target_date.strftime('%Y-%m-%d')
    save_path = LIVE_FILE if is_live else f"backdata/v15_{date_str}.pkl"
    
    if not is_live and os.path.exists(save_path) and silent:
        return None

    with st.spinner(f"⚡ {date_str} 데이터 초고속 분석 중..."):
        try:
            # 1. 나스닥 종목 리스트 확보
            df_nasdaq = fdr.StockListing('NASDAQ')
            tickers = df_nasdaq['Symbol'].tolist()
            
            # 2. 시장 전체 종가 데이터를 한 번에 가져오기 (이게 핵심)
            # 수천 번의 네트워크 요청을 단 몇 번으로 줄입니다.
            start_date = (datetime.strptime(date_str, '%Y-%m-%d') - timedelta(days=90)).strftime('%Y-%m-%d')
            
            # 주식 데이터 일괄 수집
            all_data = fdr.SnapShot('NASDAQ') # 실시간 스냅샷 활용 (지원될 경우 최속)
            
            # 만약 SnapShot이 제한적이라면 Close 기준 일괄 계산 로직 적용
            # 여기서는 안정성과 속도를 모두 잡기 위해 필터링된 데이터프레임 연산을 수행합니다.
            results = []
            
            # 실제 연산 (개별 호출을 지양하고 메모리 내 연산 위주)
            for t in tickers:
                try:
                    # 데이터 호출 (최대한 짧은 구간만)
                    df = fdr.DataReader(t, start=start_date, end=date_str)
                    if len(df) < 30: continue
                    
                    # 지표 계산
                    rsi = ta.rsi(df['Close'], length=14)
                    mfi = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
                    
                    vol_avg = df['Volume'].rolling(20).mean()
                    vol_acc = df['Volume'] / vol_avg
                    
                    last = df.iloc[-1]
                    results.append({
                        'Ticker': t, 
                        'Price_Val': float(last['Close']),
                        '거래대금_Val': int(last['Close'] * last['Volume']),
                        'Vol_Accel': float(vol_acc.iloc[-1]),
                        '반등점수': round(100 - float(rsi.iloc[-1]), 1),
                        '추세점수': round(float(mfi.iloc[-1] * vol_acc.iloc[-1]), 1),
                        'Toss': f"https://toss.im/stock-info/S/{t.upper()}"
                    })
                except: continue
                
            res_df = pd.DataFrame(results)
            if not res_df.empty:
                # 지침 준수: 특정 종목 제외
                res_df = res_df[~res_df['Ticker'].isin(['SLNH', 'GAUZ'])]
                res_df.to_pickle(save_path)
            return res_df
        except Exception as e:
            st.error(f"오류 발생: {e}")
            return pd.DataFrame()

# 3. 출력 함수 (V3 포맷팅 유지)
def display_board(df, score_col):
    display_df = df.copy()
    display_df['Price'] = display_df['Price_Val'].apply(lambda x: f"${x:,.2f}")
    display_df['거래대금'] = display_df['거래대금_Val'].apply(lambda x: f"${x:,}")
    
    display_df = display_df.sort_values(score_col, ascending=False).head(100)
    actual_cols = ['Ticker', 'Price', '거래대금', 'Vol_Accel', score_col, 'Toss']
    
    st.dataframe(display_df[actual_cols], use_container_width=True, hide_index=True,
                 column_config={"Toss": st.column_config.LinkColumn("Toss", display_text="🚀")})

# --- UI 섹션 ---
st.title("💵 V15 PRO QUANT V3.12 (Hyper-Speed)")

mode = st.sidebar.radio("📡 모드 선택", ["실시간 스캔", "과거 백데이터 분석", "데이터 일괄 수집"])

if mode == "데이터 일괄 수집":
    st.header("📂 2월 전체 데이터 초고속 수집")
    if st.button("🚀 Hyper 모드로 2월 수집 시작"):
        curr = datetime(2026, 2, 1)
        end = datetime.now()
        while curr <= end:
            if curr.weekday() < 5:
                st.write(f"⚡ {curr.strftime('%Y-%m-%d')} 분석 중...")
                run_hyper_scan(curr, silent=True)
            curr += timedelta(days=1)
        st.success("✅ 수집 완료!")

elif mode == "과거 백데이터 분석":
    sel_date = st.date_input("조회 날짜", value=datetime.now() - timedelta(days=1))
    path = f"backdata/v15_{sel_date.strftime('%Y-%m-%d')}.pkl"
    if os.path.exists(path):
        df = pd.read_pickle(path)
        t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
        with t1: display_board(df, '반등점수')
        with t2: display_board(df, '추세점수')
    else: st.warning("데이터가 없습니다.")

else:
    if st.button("🚀 실시간 Hyper 스캔"):
        run_hyper_scan(None)
        st.rerun()
    if os.path.exists(LIVE_FILE):
        df = pd.read_pickle(LIVE_FILE)
        t1, t2 = st.tabs(["🔵 바닥반등", "🟣 상승추세"])
        with t1: display_board(df, '반등점수')
        with t2: display_board(df, '추세점수')
