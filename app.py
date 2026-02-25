import streamlit as st
import pandas as pd
import pandas_ta as ta
import FinanceDataReader as fdr
import os
import time
from datetime import datetime

# 1. 기본 설정 및 가독성 폰트
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")
st.markdown("""
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
    * { font-family: 'Pretendard', sans-serif !important; }
    h1 { font-weight: 800 !important; letter-spacing: -1px; }
    </style>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"

# 2. 내재화된 전체 시장 스캔 함수
def run_full_market_scan():
    all_results = []
    
    # [과정 1] 나스닥 전체 리스트 확보
    with st.spinner("📡 나스닥(NASDAQ) 전체 종목 리스트 불러오는 중..."):
        try:
            df_nasdaq = fdr.StockListing('NASDAQ')
            # 블랙리스트 제외 (GAUZ, SLNH 등)
            exclude = ['GAUZ', 'SLNH']
            tickers = [t for t in df_nasdaq['Symbol'].tolist() if t not in exclude]
        except Exception as e:
            st.error(f"리스트 확보 실패: {e}")
            return pd.DataFrame()

    total_count = len(tickers)
    st.write(f"🚀 총 {total_count}개 종목 분석을 시작합니다.")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # [과정 2] 종목별 성적표 계산 (Colab 로직 내재화)
    for i, t in enumerate(tickers):
        try:
            # 최근 데이터 수집 (안정성을 위해 최근 60일치)
            df = fdr.DataReader(t).tail(60)
            
            if len(df) < 30: continue

            # V15 성적표 과목 계산
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            
            avg_vol = df['Volume'].rolling(20).mean()
            df['Vol_Accel'] = df['Volume'] / avg_vol
            
            last = df.iloc[-1]
            
            # 성적표 데이터 생성
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
            
            # 진행 상황 업데이트 (10개 단위로 화면 표시)
            if i % 10 == 0:
                status_text.text(f"📦 분석 중: {t} ({i}/{total_count})")
                progress_bar.progress((i + 1) / total_count)
            
            # 서버 차단 방지 미세 휴식
            time.sleep(0.01)
            
        except:
            continue
            
    status_text.empty()
    progress_bar.empty()
    return pd.DataFrame(all_results)

# 3. 메인 UI
st.title("🛡️ V15 PRO - 나스닥 전체 성적표")

# 사이드바 필터
st.sidebar.header("🎛️ 리더보드 필터")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("최소 거래 가속도", 0.5, 5.0, 1.2)

# 스캔 버튼
if st.button("🔥 나스닥 전체 실시간 스캔 시작 (Colab 과정 내재화)"):
    start_time = time.time()
    updated_df = run_full_market_scan()
    
    if not updated_df.empty:
        updated_df.to_pickle(SAVE_FILE)
        end_time = time.time()
        st.success(f"✅ 스캔 완료! (소요시간: {int(end_time - start_time)}초)")
        st.rerun()
    else:
        st.error("❌ 수집된 데이터가 없습니다. 다시 시도해 주세요.")

# 성적표 표시
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # 필터 적용
    f_df = df[(df['Volume_USD'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    t1, t2 = st.tabs(["🔵 Phoenix (반등 상위)", "🟣 Alpha (추세 상위)"])
    with t1:
        st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(100), use_container_width=True, hide_index=True)
    with t2:
        st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(100), use_container_width=True, hide_index=True)
else:
    st.info("💡 버튼을 누르면 나스닥 전 종목을 스캔하여 성적표를 만듭니다. (첫 스캔은 시간이 소요될 수 있습니다)")
