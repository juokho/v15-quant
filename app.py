import streamlit as st
import pandas as pd
import pandas_ta as ta
import yfinance as yf
import os
from datetime import datetime, timedelta

# 1. 기본 설정 및 테마 제어 (워뇨띠 스타일: 다크 배경 지향)
st.set_page_config(page_title="V15 PRO QUANT", layout="wide")

# [CSS] 워뇨띠 리더보드 스타일 커스텀 디자인
st.markdown("""
    <style>
    /* 다크모드 전환 버튼 (우측 하단 고정) */
    .dark-mode-btn {
        position: fixed;
        bottom: 20px;
        right: 20px;
        z-index: 9999;
        background-color: #1E1E1E;
        color: white;
        border: 1px solid #333;
        border-radius: 50%;
        padding: 10px;
        cursor: pointer;
    }
    /* 테이블 폰트 및 스타일 조정 */
    .stTable, .stDataFrame {
        border: 1px solid #333 !important;
    }
    div[data-testid="stExpander"] {
        border: none !important;
        background-color: #121212 !important;
    }
    </style>
    <button class="dark-mode-btn" onclick="document.body.classList.toggle('dark-mode')">🌓</button>
""", unsafe_allow_html=True)

SAVE_FILE = "v15_analyzed.pkl"
TRACKER_FILE = "portfolio_tracker.csv"

# 제공해주신 토스 로고 Base64 (image_b30207.png 기반)
TOSS_LOGO_B64 = "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQAAAQABAAD/2wCEAAkGBw8NDw4ODg0ODQ4QDQ0QDQ0NDQ8NDRARFREWFhYRFhMkHjQsGBslGxMVITIiMSk3Li8uFx8/ODM4Nyg5LisBCgoKDg0OGhAQGi0mHSYtLS0tLS03Ky0tLTI1LSstLy0tMy8tLS0rKystLS0tLS0tLSs2MC0tKzAtLjcxLy0rL//AABEIALoBEAMBEQACEQEDEQH/xAAcAAEAAQUBAQAAAAAAAAAAAAAABgIDBAUHAQj/xAA8EAACAgADBAcECAUFAQAAAAAAAQIDBAURBhIhMQcTQVFhcaEyQlKBIoKRkqKxsvAjYsHC0SRDRFNyFP/EABsBAQACAwEBAAAAAAAAAAAAAAABBQIDBgQH/88AVmV4NEXov8eTfgzXxW5qy7ns5nVeY4eGIq4a6xsrb1lXYvag/tT8U0+04XV6W+myzjv/uPF0+HNXLSLQ2h5m0AAAAAAAAAAAAAAAAAAAAAAhXSZmjrprw0Xo7XvWafBF8F83+kuuDafnyTknu7PNR8az8tIxR39Z8v9/JzCTOpiHPRCnUllsJhGy5GRjMMZhfrZrmGq0Mus1S0yjOZW71833cF8iww12rELjT12xRCxvm7Zs2eqY2NnqmRsjZVvDZGxqNjZPOiDMnDF3YZv6F1Lmlrysra5ecZS+6jn/6hwROGuXvidvZP5WvDMm1po66ciugAAAAAAAAAAAAAAAAAAAAADknSNe54+yPZXCqC+6pfnJnW8Hptponxmft9HJcVvzaq0eG0fDf6opJlvDwwo1JSak7J2eqRGyJhfrsNdqtdqs2NmkXLuTZomOuzzTXe0Qh2JnrJvxZaU6L/ABx02I2GxM1VqQ2YbKkyNkbKkyEbPdSEJZ0XQcs0oa92vESl5dW4/nJFRxyYjR2375j5vfw+P+Z3E4dfAAAAAAAAAAAAAAAAAAAAAAHJukjDOGOlPstrrmn2cFuP9J1nBsnNp9vCZ+7k+LY+XUzPjET9PoiMi5h4IW2SzeakpeajY2eqY2Rsyrbd3DTfe2l+/kzTEb5Yaq13zRCM2Hthb1URM4ZSuxZmwmFaZDGVaZixe6kIdO6GsreuJxslw0WHqffxU7H6V+py39RaiPQwx5z8o+q34bj6TefJ1E5hagAAAAAAAAAAAAAAAAAAAAAEa25yF43DqVa1vp1lWvji/ah58E14rxLHhmrjT5fS/TPb91bxLSTnx71/VHZ9nH7YtNpppp6NPg0+47Ks79jluxZZmzUsySpYSpbJSv5rLdoqh3refz4/1NWLre0sNPG+W1mhkemFlClI2VZK0ZsZVohjKtEMWblOXW4y+vD0x3rLJaLuiu2b8EtW/I8+o1FMGOcl+yP5t7WeLHOS0Vh9DZJlleCw9OGq9iqCWr4OT5ym/Ftt/M+d6jPbPltkv2z/AD4Okx44pWKx3M40swAAAAAAAAAAAAAAAAAAAAAABFtqNjKcc3bW1RiHzklrXZ/7Xf4r1LTRcUyaf0bda/GPL7K3WcOpnnmr0t8/NzTONm8Zg2+uoluLX+LWusq0795cvnodNp9fgz/pt18J6T/PJRZtHmw/qv08e5p2e151LRKVKjq0u9pfaJnaN077Gfz1sUVyikjDBHo7p0dfQ38WoZ6Ie6HiRtg3VJGSFaRDFewuHndOFVUJWWTkowhFayk32I15MlcdZtadohNazado7Xctg9kY5ZU52bs8XbFdbNcVCPPqovu732teCOF4pxK2rvtXpSOyPrP86L3S6aMNevalZVPWAAAAAAAAAAAAAAAAAAAAAAAAAABr8XkeEvetuEw85P3pVQ3/AL2mpvx6rPj6VvMe2Wm+nxX/AFVhgS2 My1/8OHynYl+o9EcT1cfvn4NX9jp//EMHP9ncBhMJfbXhKozjDSEmnKUZSaimm+T1Zu0us1ObPWtrztu8mvwYcOmvaKx2fPo4jmFm/ZN+LOzpG0RCnwV5aRDF0NtW80NsIVJEo3bDJcmxGOtVOGqdkuG8+UIL4py91ftHm1OqxaenPknaPjPk2YsVsk7Vh2vYzY2jK4770uxUo6WXtcIr4K12R8eb9FxHEeJ5NXbbspHZH1n1rvT6WuGPGUoKx6gAAAAAAAAAAAAAAAAAAAAAAAAAAAAABFuknEdXgJfzWwj6OX9pacHpzamPVEqrjE/48V8ZiPr9HB5vVs7WFVClI21hK7TTKyUYQhKc5PSMIRcpSfckuZla9aRvadoIiZnaE92Z6Mb792zHSeGq4PqY6SxEl3Psh6vwRz+t4/jumpvXBHNPj3flYYeH2t1v0j4uqZTlVGCrVOGqjVWuyK4yfxSlzk/FnK58+TPfnyTvP89y2x46442rDNNLMAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAIf0n4K+/BwjRVZc1enKNUXOSW7Ja6LzLXhGamLNM3nbp3+cKzieK+SleWN9p3+Eub4HYDM72v9K6ov3r5xrS+rrr6HQX4vpafu38v5s8NNFnt3beaWZR0URWksZinLlrVhlury6x818kV2f+obdmGm3rn7fl7MfDY/fPuTrJ8hwmBju4bDwq1Wkppb1kvOb4v7Sj1Grzaid8tpn5e7sWGPDTH+mGyPO2gAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAD//Z"

# 2. 데이터 처리 함수 (GAUZ, SLNH 집중 관리)
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
                'TOSS_LOGO': TOSS_LOGO_B64, # 제공받은 이미지 데이터
                'TOSS_LINK': f"https://tossinvest.com/stocks/{t}",
                '반등점수': 100 - float(last['RSI']),
                '추세점수': float(last['MFI'])
            })
        except: continue
    return pd.DataFrame(all_results)

def record_top_picks(df):
    today = datetime.now().strftime("%Y-%m-%d")
    new_records = df.sort_values("반등점수", ascending=False).head(5)[['Ticker', 'Price']].copy()
    new_records['Date'] = today
    new_records['Strategy'] = "Phoenix"
    new_records.rename(columns={'Price': 'Buy_Price'}, inplace=True)
    
    if os.path.exists(TRACKER_FILE):
        old_df = pd.read_csv(TRACKER_FILE)
        final_df = pd.concat([old_df, new_records], ignore_index=True)
    else:
        final_df = new_records
    final_df.to_csv(TRACKER_FILE, index=False)
    st.toast("✅ WONYOTTI LEADERBOARD UPDATED.")

# --- 메인 UI 레이아웃 ---
st.title("🏆 V15 PRO QUANT - LEADERBOARD")

# 좌측 사이드바: 과거 기록 (이미지_b2952b.png 스타일)
st.sidebar.markdown("### 📂 HISTORY ARCHIVE")
if os.path.exists(TRACKER_FILE):
    hist_df = pd.read_csv(TRACKER_FILE)
    available_dates = sorted(hist_df['Date'].unique(), reverse=True)
    selected_date = st.sidebar.selectbox("Select Date", ["None"] + available_dates)
    
    if selected_date != "None":
        st.subheader(f"📅 {selected_date} PERFORMANCE")
        # 과거 기록은 깔끔하게 텍스트 위주로 표시 (사용자 요청)
        st.table(hist_df[hist_df['Date'] == selected_date][['Strategy', 'Ticker', 'Buy_Price']])

st.markdown("---")

# 실시간 전광판 (워뇨띠 스타일 + 토스 이미지)
st.subheader("📡 REAL-TIME TERMINAL")
if st.button("🔥 START SCAN"):
    with st.spinner("FETCHING MARKET DATA..."):
        # GAUZ, SLNH 포함 집중 관리 리스트
        target_list = ["AAPL", "TSLA", "NVDA", "GAUZ", "SLNH", "005930", "MSFT"]
        df_real = run_realtime_scan(target_list)
        df_real.to_pickle(SAVE_FILE)
        st.rerun()

if os.path.exists(SAVE_FILE):
    df = pd.read_pickle(SAVE_FILE)
    
    # [설정] 워뇨띠 리더보드 그리드 설정 (토스 이미지 열 포함)
    term_cfg = {
        "Ticker": st.column_config.TextColumn("ASSET"),
        "Price": st.column_config.NumberColumn("PRICE", format="$%.2f"),
        "TOSS_LOGO": st.column_config.ImageColumn("TOSS", help="TOSS INVEST"), # 로고 이미지 표시
        "TOSS_LINK": st.column_config.LinkColumn("TRADE", display_text="GO"), # 클릭 링크
        "RSI": st.column_config.ProgressColumn("RSI", min_value=0, max_value=100)
    }
    
    st.dataframe(
        df.sort_values("반등점수", ascending=False),
        column_config=term_cfg,
        hide_index=True,
        use_container_width=True
    )
    
    if st.button("💾 SAVE TOP PICKS"):
        record_top_picks(df)
else:
    st.info("PRESS THE SCAN BUTTON TO START.")
