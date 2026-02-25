import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime, timedelta

# 1. 기본 설정
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")
SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 사용자가 제공한 토스 로고 Base64 데이터
TOSS_LOGO_BASE64 = "data:image/jpeg;base64,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"

# 2. 데이터 업데이트 및 스캔 함수
def run_realtime_scan(ticker_list):
    all_results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, t in enumerate(ticker_list):
        try:
            full_ticker = f"{t}.KS" if t.isdigit() or t in ["GAUZ", "SLNH"] else t
            status_text.text(f"🔍 스캔 중: {full_ticker} ({i+1}/{len(ticker_list)})")
            
            df = yf.download(full_ticker, period="1y", interval="1d", progress=False)
            if len(df) < 20: continue

            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MFI'] = ta.mfi(df['High'], df['Low'], df['Close'], df['Volume'], length=14)
            
            avg_vol = df['Volume'].rolling(20).mean()
            df['Vol_Accel'] = df['Volume'] / avg_vol
            df['Avg_Range'] = (abs(df['High'] - df['Low']) / df['Close'] * 100).rolling(20).mean()
            
            last = df.iloc[-1]
            all_results.append({
                'Ticker': t,
                'Price': round(float(last['Close']), 2),
                'RSI': round(float(last['RSI']), 2),
                'MFI': round(float(last['MFI']), 2),
                'Vol_Accel': round(float(last['Vol_Accel']), 2),
                'Avg_Range': round(float(last['Avg_Range']), 2),
                'Volume_USD': float(last['Close'] * last['Volume']),
                '반등점수': 100 - float(last['RSI']),
                '추세점수': float(last['MFI'] * last['Vol_Accel']),
                'TOSS': f"https://tossinvest.com/stocks/{t}" 
            })
        except Exception as e:
            continue
        progress_bar.progress((i + 1) / len(ticker_list))
    
    status_text.empty()
    return pd.DataFrame(all_results)

# 3. 기록 저장 함수
def record_to_history(df):
    today = datetime.now().strftime("%Y-%m-%d")
    new_records = []
    
    p_top5 = df.sort_values(by="반등점수", ascending=False).head(5)
    a_top5 = df.sort_values(by="추세점수", ascending=False).head(5)
    
    for _, row in p_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': 'Phoenix', 'Ticker': row['Ticker'], 'Buy_Price': row['Price']})
    for _, row in a_top5.iterrows():
        new_records.append({'Date': today, 'Strategy': 'Alpha', 'Ticker': row['Ticker'], 'Buy_Price': row['Price']})
    
    new_df = pd.DataFrame(new_records)
    if os.path.exists(TRACKER_FILE):
        old_df = pd.read_csv(TRACKER_FILE)
        old_df = old_df[old_df['Date'] != today]
        final_df = pd.concat([old_df, new_df], ignore_index=True)
    else:
        final_df = new_df
    
    final_df.to_csv(TRACKER_FILE, index=False)
    st.toast(f"✅ {today} 상위 종목 기록 완료!")

# --- UI 레이아웃 시작 ---
st.title("🛡️ V15 PRO - 전광판 & 타임라인 통합")

# 사이드바
st.sidebar.header("🎛️ 전광판 필터")
min_val = st.sidebar.number_input("최소 거래대금 ($)", value=1000000)
min_vol_acc = st.sidebar.slider("최소 거래 가속도", 0.5, 5.0, 1.0)

st.sidebar.markdown("---")
st.sidebar.header("📂 과거 기록 보관소")
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    available_dates = sorted(hist_df['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("📅 날짜 선택", ["선택 안 함"] + available_dates)
else:
    selected_date = "선택 안 함"

# 메인 버튼
c1, _ = st.columns([1, 1])
if c1.button("🔥 실시간 전종목 스캔 시작"):
    sample_list = ["AAPL", "TSLA", "NVDA", "MSFT", "GOOGL", "GAUZ", "SLNH", "005930"]
    updated_df = run_realtime_scan(sample_list)
    updated_df.to_pickle(SAVE_FILE)
    st.rerun()

# --- 1. 과거 기록 보관소 (백테스트) 섹션 : TOSS 열 완전히 제거 ---
if selected_date != "선택 안 함":
    st.subheader(f"📅 {selected_date} 전략 타임라인 성적표")
    target_picks = hist_df[hist_df['Date'] == selected_date].copy()
    
    if st.button("📈 1일/3일/7일 수익률 분석"):
        with st.spinner("분석 중..."):
            results = []
            base_date = datetime.strptime(selected_date, "%Y-%m-%d")
            for _, row in target_picks.iterrows():
                ticker = row['Ticker']
                buy_price = float(row['Buy_Price'])
                end_date = (base_date + timedelta(days=15)).strftime("%Y-%m-%d")
                df_history = yf.download(ticker, start=selected_date, end=end_date, progress=False)
                
                if not df_history.empty:
                    prices = df_history['Close'].tolist()
                    p1 = prices[1] if len(prices) > 1 else None
                    p3 = prices[3] if len(prices) > 3 else None
                    p7 = prices[7] if len(prices) > 7 else None
                    
                    def calc_ret(p, b): return f"{round(((p-b)/b*100),2)}%" if p else "대기"

                    results.append({
                        'Strategy': row['Strategy'], 'Ticker': ticker, 'Buy_Price': buy_price,
                        '1일 후': calc_ret(p1, buy_price), '3일 후': calc_ret(p3, buy_price), '7일 후': calc_ret(p7, buy_price)
                    })
            st.table(pd.DataFrame(results)) 
    else:
        st.table(target_picks)
    st.markdown("---")

# --- 2. 실시간 전광판 섹션 : TOSS 열 포함 (이미지 아이콘 활용) ---
st.subheader("📊 오늘의 실시간 전광판")
if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    if 'TOSS' not in df.columns:
        df['TOSS'] = df['Ticker'].apply(lambda x: f"https://tossinvest.com/stocks/{x}")
        
    f_df = df[(df['Volume_USD'] >= min_val) & (df['Vol_Accel'] >= min_vol_acc)].copy()
    
    # 전광판용 컬럼 설정 (TOSS 이미지 아이콘 적용)
    realtime_cfg = {
        "Price": st.column_config.NumberColumn("Price", format="%.2f"),
        "TOSS": st.column_config.LinkColumn(
            "TOSS", 
            display_text="📲 TOSS", # 스트림릿 정책상 텍스트와 함께 표시
            help="클릭 시 토스증권 상세 페이지로 이동"
        ),
    }
    
    t1, t2 = st.tabs(["🔵 Phoenix (반등)", "🟣 Alpha (추세)"])
    with t1:
        st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(50), 
                     column_config=realtime_cfg, hide_index=True, use_container_width=True)
    with t2:
        st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(50), 
                     column_config=realtime_cfg, hide_index=True, use_container_width=True)
    
    if st.button("💾 이 리스트를 오늘의 TOP으로 저장"):
        record_to_history(df)
else:
    st.info("스캔 시작 버튼을 눌러주세요.")
