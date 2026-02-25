
import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="V15 PRO QUANT", layout="wide")
SAVE_FILE = "v15_analyzed.pkl"
TOSS_LOGO = "https://static.toss.im/assets/homepage/safety/icn-security-fill.png"

st.title("🛡️ V15 PRO - 전문가용 필터 대시보드")

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
        t1, t2 = st.tabs(["🔵 Phoenix (반등)", "🟣 Alpha (추세)"])
        cfg = {
            "Vol_Accel": st.column_config.NumberColumn("거래가속", format="%.1fx"),
            "Avg_Range": st.column_config.NumberColumn("평균변동", format="%.1f%%"),
            "Volume_USD": st.column_config.NumberColumn("거래대금($)", format="%d"),
            "TOSS": st.column_config.LinkColumn("GO", display_text="LINK")
        }
        with t1: st.dataframe(f_df.sort_values(by="반등점수", ascending=False).head(50), column_config=cfg, hide_index=True)
        with t2: st.dataframe(f_df.sort_values(by="추세점수", ascending=False).head(50), column_config=cfg, hide_index=True)
    else:
        st.warning("조건을 만족하는 종목이 없습니다. 필터를 완화해 보세요.")
