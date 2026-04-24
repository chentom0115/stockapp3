import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="韭菜選股 V1 - 專業修正版", layout="wide")
st.title("🚀 韭菜選股 V1")

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 選股核心設定")
模式 = st.sidebar.radio("選擇操作模式", ["釣魚穩健型 (看回測)", "搶短爆發型 (看噴發)"])

if 模式 == "釣魚穩健型 (看回測)":
    st.sidebar.markdown("---")
    dist_threshold = st.sidebar.slider("距離支撐門檻 (%)", 0.5, 8.0, 4.5)
    min_rr_ratio = st.sidebar.slider("最低風報比要求", 1.0, 5.0, 2.0)
else:
    st.sidebar.markdown("---")
    change_threshold = st.sidebar.slider("今日最低漲幅 (%)", 1.0, 7.0, 2.5)
    vol_multiplier = st.sidebar.slider("量能爆發倍數", 1.0, 3.0, 1.5)

target_group = st.sidebar.selectbox("3. 選擇魚池", 
    ["全部電子股 (依成交值排序)", "AI 伺服器/代工", "CPO 矽光子", "低軌衛星概念", "載板三雄"])

# 初始化 Session State
if 'final_df' not in st.session_state:
    st.session_state.final_df = None

# --- 1. 執行掃描 ---
if st.sidebar.button("🚀 開始全自動掃描"):
    groups = {
        "AI 伺服器/代工": {"2330.TW": "台積電", "2317.TW": "鴻海", "2382.TW": "廣達", "3231.TW": "緯創", "6669.TW": "緯穎", "3017.TW": "奇鋐", "2376.TW": "技嘉"},
        "CPO 矽光子": {"3665.TW": "貿聯-KY", "6442.TW": "光聖", "3081.TW": "聯亞", "3363.TWO": "上詮", "3163.TWO": "波若威", "4979.TWO": "華星光"},
        "低軌衛星概念": {"2313.TW": "華通", "2314.TW": "台揚", "3491.TWO": "昇達科", "6274.TWO": "台燿", "2383.TW": "台光電"},
        "載板三雄": {"3037.TW": "欣興", "8046.TW": "南電", "3189.TW": "景碩", "2368.TW": "金像電"}
    }
    
    target_dict = {}
    
    if "全部電子股" in target_group:
        dl = DataLoader()
        # 抓取最近 5 天的資料確保有交易日數據
        start_dt = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        try:
            df_price = dl.taiwan_stock_month_total(start_date=start_dt)
            df_info = dl.taiwan_stock_info()
            
            if not df_price.empty:
                last_date = df_price['date'].max()
                df_latest = df_price[df_price['date'] == last_date].copy()
                merged = pd.merge(df_latest, df_info, on='stock_id')
                
                # 過濾產業：加入關鍵的「電腦及週邊設備業」
                keywords = '電子|半導體|光電|電腦及週邊|通信網路'
                elec_df = merged[merged['industry_category'].str.contains(keywords, na=False)].copy()
                
                # 依成交金額排序取前 150 名
                elec_df = elec_df.sort_values(by='turnover', ascending=False).head(150)
                
                for _, row in elec_df.iterrows():
                    suffix = ".TW" if row['type'] == 'twse' else ".TWO"
                    target_dict[f"{row['stock_id']}{suffix}"] = row['stock_name']
        except Exception as e:
            st.error(f"資料讀取錯誤: {e}")
    else:
        target_dict = groups[target_group]

    # 開始掃描數據
    all_results = []
    progress_bar = st.progress(0)
    count = 0
    total = len(target_dict)

    if total == 0:
        st.error("找不到符合魚池的標的，請確認網路連線或資料來源。")
    else:
        for symbol, name in target_dict.items():
            try:
                df = yf.Ticker(symbol).history(period="6mo")
                if df.empty or len(df) < 22: continue
                
                p = df['Close'].iloc[-1].item()
                p_prev = df['Close'].iloc[-2].item()
                m5 = df['Close'].rolling(5).mean().iloc[-1].item()
                m20 = df['Close'].rolling(20).mean().iloc[-1].item()
                v_today = df['Volume'].iloc[-1].item()
                v_avg = df['Volume'].rolling(5).mean().iloc[-1].item()
                high
