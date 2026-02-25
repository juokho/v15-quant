import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime

# 1. 기본 설정 및 폰트
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif !important; }
    h1 { font-weight: 800 !important; letter-spacing: -1px; }
    </style>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 2. 강화된 스캔 함수
def run_realtime_scan(ticker_list):
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(ticker_list):
        try:
            # 티커 처리 (V1 기준 유지)
            full_ticker = f"{t}.KS" if t in ["005930", "GAUZ", "SLNH"] else t
            status_text.text(f"🔍 스캔 중: {full_ticker} ({i+1}/{len(ticker_list)})")
            
            # 데이터 다운로드 (최근 1년)
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            
            # 데이터 검증: 최소 20일치 이상의 데이터가 있는지 확인
            if df is None or len(df) < 20:
                continue

            # 지표 계산
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            
            # 거래 가속도 및 변동성 계산
            avg_vol = df['Volume'].rolling(20).mean()
            df['Vol_Accel'] = df['Volume'] / avg_vol
            df['Avg_Range'] = (abs(df['High'] - df['Low']) / df['Close'] * 100).rolling(20).mean()
            
            # 마지막 행 데이터 추출
            last = df.iloc[-1]
            
            # 데이터 안전하게 추출 (NaN 값 방지)
            res = {
                'Ticker': t,
                'Price': round(float(last['Close']), 2),
                'RSI': round(float(last['RSI']), 2) if not pd.isna(last['RSI']) else 50.0,
                'MFI': round(float(last['MFI']), 2) if not pd.isna(last['MFI']) else 50.0,
                'Vol_Accel': round(float(last['Vol_Accel']), 2) if not pd.isna(last['Vol_Accel']) else 1.0,
                'Avg_Range': round(float(last['Avg_Range']), 2) if not pd.isna(last['Avg_Range']) else 0.0,
                'Volume_USD': float(last['Close'] * last['Volume']),
                '반등점수': 100 - float(last['RSI']) if not pd.isna(last['RSI']) else 0.0,
                '추세점수': float(last['MFI'] * last['Vol_Accel']) if not (pd.isna(last['MFI']) or pd.isna(last['Vol_Accel'])) else 0.0
            }
            all_results.append(res)
            
        except Exception as e:
            st.warning(f"⚠️ {t} 스캔 실패: {e}")
            continue
        finally:
            progress_bar.progress((i + 1) / len(ticker_list))
    
    status_text.empty()
    
    # 결과가 없으면 빈 데이터프레임 대신 컬럼이 고정된 데이터프레임 반환
    if not all_results:
        return pd.DataFrame(columns=['Ticker', 'Price', 'RSI', 'MFI', 'Vol_Accel', 'Avg_Range', 'Volume_USD', '반등점수', '추세점수'])
        
    return pd.DataFrame(all_results)

# 3. 메인 UI
st.title("🛡️ V15 PRO - 전광판 시스템")

# 사이드바 필터
st.sidebar.header("🎛️ 필터 설정")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("최소 거래 가속도", 0.5, 5.0, 1.0)

# 초기화 버튼
if st.sidebar.button("🗑️ 기존 데이터 완전 삭제"):
    if os.path.exists(SAVE_FILE):
        os.remove(SAVE_FILE)
        st.success("데이터가 삭제되었습니다. 다시 스캔하세요.")
        st.rerun()

# 스캔 시작
if st.button("🔥 실시간 전종목 스캔 시작"):
    # 사용자 집중 관리 종목 포함
    sample_list = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "GAUZ", "SLNH", "005930"]
    updated_df = run_realtime_scan(sample_list)
    
    if not updated_df.empty:
        updated_df.to_pickle(SAVE_FILE)
        st.success("스캔 완료!")
        st.rerun()
    else:
        st.error("스캔된 데이터가 없습니다. 종목 리스트나 연결 상태를 확인하세요.")

# 데이터 표시
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # 열 존재 여부 체크 및 강제 보정
    required_cols = ['Volume_USD', 'Vol_Accel', '반등점수', '추세점수']
    missing_cols = [c for c in required_cols if c not in df.columns]
    
    if missing_cols:
        st.error(f"⚠️ 데이터 구조 결함 (누락: {missing_cols}). 다시 스캔해 주세요.")
    else:
        f_df = df[(df['Volume_USD'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
        
        t1, t2 = st.tabs(["🔵 Phoenix (반등)", "🟣 Alpha (추세)"])
        with t1:
            st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(50), use_container_width=True, hide_index=True)
        with t2:
            st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(50), use_container_width=True, hide_index=True)
else:
    st.info("💡 위 버튼을 눌러 스캔을 시작해 주세요.")
