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
        # 抓取最近 3 天的資料確保有交易日數據
        start_dt = (datetime.now() - timedelta(days=5)).strftime('%Y-%m-%d')
        df_price = dl.taiwan_stock_month_total(start_date=start_dt)
        df_info = dl.taiwan_stock_info()
        
        if not df_price.empty:
            # 1. 取得最後一個交易日的資料
            last_date = df_price['date'].max()
            df_latest = df_price[df_price['date'] == last_date].copy()
            
            # 2. 合併產業資訊
            merged = pd.merge(df_latest, df_info, on='stock_id')
            
            # 3. 過濾產業：加入關鍵的「電腦及週邊設備業」(緯穎所在分類)
            keywords = '電子|半導體|光電|電腦及週邊|通信網路'
            elec_df = merged[merged['industry_category'].str.contains(keywords, na=False)].copy()
            
            # 4. 依成交金額 (turnover) 排序，取前 150 名
            elec_df = elec_df.sort_values(by='turnover', ascending=False).head(150)
            
            # 5. 建立標的字典
            for _, row in elec_df.iterrows():
                # 判斷上市或上櫃 (yfinance 結尾不同)
                suffix = ".TW" if row['type'] == 'twse' else ".TWO"
                target_dict[f"{row['stock_id']}{suffix}"] = row['stock_name']
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
                
                p = df['Close'].iloc[-1]
                p_prev = df['Close'].iloc[-2]
                m5 = df['Close'].rolling(5).mean().iloc[-1]
                m20 = df['Close'].rolling(20).mean().iloc[-1]
                v_today = df['Volume'].iloc[-1]
                v_avg = df['Volume'].rolling(5).mean().iloc[-1]
                high_6mo = df['High'].max()
                change = (p - p_prev) / p_prev * 100

                if "釣魚" in 模式:
                    dist_20 = (p - m20) / m20 * 100
                    if 0 <= dist_20 <= dist_threshold:
                        reward = high_6mo - p
                        risk = p - (m20 * 0.98)
                        ratio = round(reward / risk, 2) if risk > 0 else 0
                        if ratio >= min_rr_ratio:
                            all_results.append({"名稱": name, "代碼": symbol, "價格": round(p, 2), "風報比": ratio, "診斷": "💎 回測支撐"})
                else:
                    if change >= change_threshold and v_today >= v_avg * vol_multiplier and p > m5:
                        all_results.append({"名稱": name, "代碼": symbol, "價格": round(p, 2), "漲幅%": f"{change:.2f}%", "診斷": "🔥 動能噴發"})
                
                time.sleep(0.02) # 稍微加速掃描
            except:
                continue
            finally:
                count += 1
                progress_bar.progress(count / total)

        st.session_state.final_df = pd.DataFrame(all_results) if all_results else None

# --- 2. 顯示排行榜 ---
if st.session_state.final_df is not None:
    st.subheader(f"🏆 {
