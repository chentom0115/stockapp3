import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import time

st.set_page_config(page_title="股王釣魚 V8 AI App", layout="wide")
st.title("🎣 股王釣魚 V8：AI 選股 App")

# 側邊欄控制項
mode = st.sidebar.selectbox("選股模式", ["釣魚穩健型", "搶短爆發型"])
threshold = st.sidebar.slider("最低門檻", 0, 100, 60)
scan_num = st.sidebar.slider("掃描數量", 20, 200, 50)

if st.sidebar.button("啟動全自動掃描"):
    dl = DataLoader()
    df_info = dl.taiwan_stock_info()
    elec_df = df_info[df_info['industry_category'].str.contains('電子|半導體|光電', na=False)]
    name_map = dict(zip(elec_df['stock_id'], elec_df['stock_name']))
    raw_list = elec_df['stock_id'].head(scan_num).tolist()
    
    all_results = []
    progress_bar = st.progress(0)
    
    for i, code in enumerate(raw_list):
        symbol = f"{code}.TW"
        try:
            df = yf.Ticker(symbol).history(period="3mo")
            if df.empty:
                df = yf.Ticker(f"{code}.TWO").history(period="3mo")
            if not df.empty and len(df) > 20:
                p = df['Close'].iloc[-1]
                m5 = df['Close'].rolling(5).mean().iloc[-1]
                m20 = df['Close'].rolling(20).mean().iloc[-1]
                change = (p - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100
                score = 100 if p > m5 and change > 2 else 50
                if score >= threshold:
                    all_results.append({"代碼": symbol, "名稱": name_map.get(code, "未知"), "價格": round(p, 2), "得分": score})
        except: continue
        progress_bar.progress((i + 1) / scan_num)

    if all_results:
        st.table(pd.DataFrame(all_results))
    else:
        st.warning("目前無符合條件標的")
