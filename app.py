import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime

# 1. 기본 설정 (워뇨띠 스타일 다크 테마)
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

# [CSS] 불필요한 디자인 제거, 본질에 집중한 깔끔한 스타일
st.markdown("""
    <style>
    /* 다크모드 대응 배경 및 폰트 */
    .reportview-container { background: #0E1117; }
    .stDataFrame { border: 1px solid #333 !important; }
    
    /* 하단 고정 다크모드 버튼 (간결한 버전) */
    .floating-btn {
        position: fixed; bottom: 20px; right: 20px; z-index: 1000;
        background: #1E1E1E; color: white; border: 1px solid #444;
        padding: 10px; border-radius: 50%; cursor: pointer;
    }
    </style>
""", unsafe_allow_html=True)

# 파일명 충돌을 피하기 위해 새로운 파일명 사용
SAVE_FILE = "v15_final_backup.pkl"

# 2. 데이터 처리 (수치 분석 전용)
def run_realtime_scan(ticker_list):
    all_results = []
    for t in ticker_list:
        try:
            # GAUZ, SLNH 및 한국 종목 처리
            full_ticker = f"{t}.KS" if t.isdigit() or t in ["GAUZ", "SLNH"] else t
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if df.empty: continue
            
            # RSI 및 주요 지표 계산
            df['RSI'] = ta.rsi(df['Close'], length=14)
            last = df.iloc[-1]
            
            all_results.append({
                'Ticker': t,
                'Price': round(float(last['Close']), 2), # "현재가" 대신 "Price"
                'RSI': round(float(last['RSI']), 2),
                'Score': round(100 - float(last['RSI']), 2) # 반등 점수
            })
        except: continue
    return pd.DataFrame(all_results)

# 3. 메인 UI
st.title("🏆 V15 PRO QUANT - LEADERBOARD")
st.info("🔄 토스 이미지 통합 전의 안정적인 버전으로 복구되었습니다.")

# 분석 시작 버튼
if st.button("🔥 START ANALYSIS"):
    with st.spinner("MARKET DATA SCANNING..."):
        # 집중 관리 종목 리스트
        target_list = ["AAPL", "TSLA", "NVDA", "GAUZ", "SLNH", "005930", "MSFT"]
        df_real = run_realtime_scan(target_list)
        df_real.to_pickle(SAVE_FILE)
        st.rerun()

# 결과 출력 섹션
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # 열 이름이 예전 것과 섞여서 에러 나는 것을 방지하는 안전장치
    if "Score" not in df.columns:
        st.error("⚠️ 이전 데이터 형식이 감지되었습니다. 'START ANALYSIS'를 눌러 새로 고침하세요.")
    else:
        # 그리드 설정 (깔끔한 텍스트 기반)
        grid_cfg = {
            "Ticker": st.column_config.TextColumn("💎 ASSET"),
            "Price": st.column_config.NumberColumn("💵 PRICE", format="$%.2f"),
            "RSI": st.column_config.NumberColumn("📊 RSI", format="%.2f"),
            "Score": st.column_config.NumberColumn("🎯 SCORE", format="%.1f")
        }

        # 최종 정렬 및 출력
        st.dataframe(
            df.sort_values("Score", ascending=False),
            column_config=grid_cfg,
            hide_index=True,
            use_container_width=True
        )
else:
    st.write("💡 데이터가 없습니다. 분석 시작 버튼을 눌러주세요.")
