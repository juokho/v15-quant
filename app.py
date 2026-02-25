import streamlit as st
import pandas as pd
import yfinance as yf
import os
from datetime import datetime

st.set_page_config(page_title="V15 PRO QUANT", layout="wide")
SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv" # 백테스트 기록용 파일

# ---------------------------------------------------------
# 1. 데이터 업데이트 함수 (여기에 기존 Colab 코드를 이식해야 합니다)
# ---------------------------------------------------------
def run_data_update():
    st.info("데이터 수집 및 분석을 시작합니다. (시간이 소요될 수 있습니다...)")
    # TODO: 여기에 기존 코랩에서 쓰시던 yfinance 다운로드 및 pandas-ta 계산 코드를 넣으세요.
    # 예시:
    # df = fetch_and_analyze_data()
    # df.to_pickle(SAVE_FILE)
    st.success("데이터 업데이트가 완료되었습니다! 페이지를 새로고침 해주세요.")

# ---------------------------------------------------------
# 2. 상위 종목 기록 함수 (오늘의 Top 5 저장)
# ---------------------------------------------------------
def record_top_picks(df):
    today = datetime.now().strftime("%Y-%m-%d")
    
    # 이미 오늘 기록을 남겼는지 확인
    if os.path.exists(TRACKER_FILE):
        history_df = pd.read_csv(TRACKER_FILE)
        if today in history_df['Date'].values:
            st.toast("오늘의 종목이 이미 기록되어 있습니다.")
            return history_df
    else:
        history_df = pd.DataFrame(columns=['Date', 'Strategy', 'Ticker', 'Buy_Price'])

    # 반등(Phoenix) 및 추세(Alpha) 상위 5개 추출
    phoenix_top5 = df.sort_values(by="반등점수", ascending=False).head(5)
    alpha_top5 = df.sort_values(by="추세점수", ascending=False).head(5)

    new_records = []
    
    # 상위 종목 기록
    for _, row in phoenix_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': 'Phoenix', 'Ticker': row['Ticker'], 'Buy_Price': row['price']})
    for _, row in alpha_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': 'Alpha', 'Ticker': row['Ticker'], 'Buy_Price': row['price']})
        
    # 집중 관리 종목 (GAUZ, SLNH) 강제 추가
    for focus_ticker in ['GAUZ.KS', 'SLNH.KS']: # 실제 티커명으로 수정 필요
        if focus_ticker in df['Ticker'].values:
            price = df[df['Ticker'] == focus_ticker]['현재가'].values[0]
            new_records.append({'Date': today, 'Strategy': 'Focus Management', 'Ticker': focus_ticker, 'Buy_Price': price})

    new_df = pd.DataFrame(new_records)
    history_df = pd.concat([history_df, new_df], ignore_index=True)
    history_df.to_csv(TRACKER_FILE, index=False)
    st.toast("오늘의 포트폴리오가 기록되었습니다!")
    return history_df

# ---------------------------------------------------------
# 화면 UI 구성
# ---------------------------------------------------------
st.title("🛡️ V15 PRO - 전문가용 필터 & 백테스트 대시보드")

# 수동 업데이트 버튼
col1, col2 = st.columns([8, 2])
with col2:
    if st.button("🔄 최신 데이터 스캔 및 업데이트"):
        run_data_update()

if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    st.sidebar.header("🎛️ 고도화 필터")
    min_val = st.sidebar.number_input("최소 거래대금 ($)", value=5000000)
    min_vol_acc = st.sidebar.slider("최소 거래 가속도 (1.0 = 평소수준)", 0.5, 5.0, 1.2)
    min_range = st.sidebar.slider("최소 평균 변동폭 (%)", 1.0, 10.0, 2.0)
    
    # 필터 적용 로직
    f_df = df[
        (df['Volume_USD'] >= min_val) & 
        (df['Vol_Accel'] >= min_vol_acc) & 
        (df['Avg_Range'] >= min_range)
    ].copy()
    
    f_df['TOSS'] = f_df['Ticker'].apply(lambda x: f"https://tossinvest.com/stocks/{x}")

    if not f_df.empty:
        # 탭 3개로 확장: 반등, 추세, 백테스트
        t1, t2, t3 = st.tabs(["🔵 Phoenix (반등)", "🟣 Alpha (추세)", "📈 백테스트 (수익률 추적)"])
        cfg = {
            "Vol_Accel": st.column_config.NumberColumn("거래가속", format="%.1fx"),
            "Avg_Range": st.column_config.NumberColumn("평균변동", format="%.1f%%"),
            "Volume_USD": st.column_config.NumberColumn("거래대금($)", format="%d"),
            "TOSS": st.column_config.LinkColumn("GO", display_text="LINK")
        }
        
        with t1: 
            st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(50), column_config=cfg, hide_index=True)
        with t2: 
            st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(50), column_config=cfg, hide_index=True)
            
        with t3:
            st.subheader("📊 누적 수익률 추적")
            if st.button("💾 오늘의 상위 5종목 기록하기"):
                record_top_picks(df)
            
            if os.path.exists(TRACKER_FILE):
                history_df = pd.read_csv(TRACKER_FILE)
                st.write("과거 추천 종목 리스트 (향후 현재가 연동 업데이트 예정):")
                st.dataframe(history_df, hide_index=True)
            else:
                st.info("아직 기록된 백테스트 데이터가 없습니다.")
    else:
        st.warning("조건을 만족하는 종목이 없습니다. 필터를 완화해 보세요.")
else:
    st.error(f"{SAVE_FILE} 파일이 없습니다. 업데이트 버튼을 눌러 데이터를 생성하세요.")
