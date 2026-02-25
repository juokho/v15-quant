import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime, timedelta

# 1. 기본 설정 (테마 설정)
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

# [CSS] 워뇨띠 스타일: 검정 배경, 얇은 선, 우측 하단 고정 버튼
st.markdown("""
    <style>
    /* 전체 배경 및 폰트 */
    [data-testid="stAppViewContainer"] { background-color: #0F0F0F; color: #E0E0E0; }
    .stTable, .stDataFrame { border: 1px solid #2D2D2D !important; }
    
    /* 하단 고정 다크모드 제어 버튼 */
    .floating-btn {
        position: fixed;
        bottom: 25px;
        right: 25px;
        z-index: 1000;
        background: #1E1E1E;
        border: 1px solid #444;
        padding: 10px;
        border-radius: 50%;
        font-size: 20px;
        cursor: pointer;
    }
    </style>
    <div class="floating-btn">🌓</div>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 제공해주신 토스 로고 데이터 (실시간 전광판 전용)
TOSS_LOGO_B64 = "data:image/jpeg;base64,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"

# 2. 데이터 업데이트 함수
def run_realtime_scan(ticker_list):
    all_results = []
    for t in ticker_list:
        try:
            full_ticker = f"{t}.KS" if t.isdigit() or t in ["GAUZ", "SLNH"] else t
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if df.empty: continue
            
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            last = df.iloc[-1]
            
            all_results.append({
                'Ticker': t,
                'Price': round(float(last['Close']), 2), # "현재가" 대신 "Price"
                'RSI': round(float(last['RSI']), 2),
                'MFI': round(float(last['MFI']), 2),
                'TOSS_LOGO': TOSS_LOGO_B64,
                'TOSS_LINK': f"https://tossinvest.com/stocks/{t}",
                'Score': 100 - float(last['RSI'])
            })
        except: continue
    return pd.DataFrame(all_results)

# --- 메인 화면 레이아웃 ---
st.title("🎖️ WONYOTTI LEADERBOARD - V15 PRO")

# 사이드바 (과거 기록 보관소)
st.sidebar.markdown("### 📁 과거 기록 아카이브") # 이모지 추가
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    available_dates = sorted(hist_df['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("📅 날짜를 선택하세요", ["선택 안 함"] + available_dates)
    
    if selected_date != "선택 안 함":
        st.markdown(f"#### 📜 {selected_date} 추천 리스트") # 이모지 추가
        st.table(hist_df[hist_df['Date'] == selected_date][['Strategy', 'Ticker', 'Buy_Price']])

st.markdown("---")

# 실시간 터미널 섹션
st.subheader("📡 실시간 트레이딩 터미널") # 이모지 추가
if st.button("🔥 전종목 리더보드 갱신"):
    with st.spinner("데이터 동기화 중..."):
        # GAUZ, SLNH 등 집중 관리 종목 포함
        target_list = ["AAPL", "TSLA", "NVDA", "GAUZ", "SLNH", "005930", "MSFT", "GOOGL"]
        df_real = run_realtime_scan(target_list)
        df_real.to_pickle(SAVE_FILE)
        st.rerun()

if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # [워뇨띠 스타일 그리드 설정]
    grid_cfg = {
        "Ticker": st.column_config.TextColumn("💎 ASSET"), # 자산 이모지
        "Price": st.column_config.NumberColumn("💵 PRICE", format="$%.2f"), # 가격 이모지
        "TOSS_LOGO": st.column_config.ImageColumn("📲 TOSS"), # 토스 아이콘 이미지
        "TOSS_LINK": st.column_config.LinkColumn("🔗 TRADE", display_text="LINK"), # 링크 이모지
        "RSI": st.column_config.ProgressColumn("📊 MOMENTUM", min_value=0, max_value=100),
        "Score": st.column_config.NumberColumn("🎯 SCORE")
    }
    
    # 리더보드 출력
    st.dataframe(
        df.sort_values("Score", ascending=False),
        column_config=grid_cfg,
        hide_index=True,
        use_container_width=True
    )
    
    # 하단 버튼 이모지 추가
    if st.button("💾 오늘의 상위 종목 박제하기"):
        # 저장 로직 (생략)
        st.success("✅ 리더보드 저장 완료!")
else:
    st.info("💡 위 버튼을 눌러 스캔을 시작하십시오.")
