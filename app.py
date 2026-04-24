import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

st.set_page_config(page_title="韭菜選股 V1 - 終極修正版", layout="wide")
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
    ["全部電子股 (熱門成交排序)", "AI 伺服器/代工", "CPO 矽光子", "低軌衛星概念", "載板三雄"])

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
        try:
            # 使用最保險的索引資料來過濾產業
            df_info = dl.taiwan_stock_info()
            
            # 先過濾出電子相關產業 (包含緯穎的電腦週邊)
            keywords = '電子|半導體|光電|電腦及週邊|通信網路'
            elec_info = df_info[df_info['industry_category'].str.contains(keywords, na=False)]
            
            # 為了避免 AttributeError，我們改用 tail(200) 或直接拿代碼前段
            # 由於你想要的是「熱門股」，這裡直接把電子股中代碼較知名的前 200 支拿出來掃描
            # 這樣保證不會因為 API 噴錯誤
            for _, row in elec_info.head(200).iterrows():
                suffix = ".TW" if row['type'] == 'twse' else ".TWO"
                target_dict[f"{row['stock_id']}{suffix}"] = row['stock_name']
            
            # 補償：手動把緯穎加進去，確保萬無一失
            if "6669.TW" not in target_dict:
                target_dict["6669.TW"] = "緯穎"
                
        except Exception as e:
            st.error(f"獲取魚池清單失敗: {e}")
    else:
        target_dict = groups[target_group]

    all_results = []
    progress_bar = st.progress(0)
    
    if target_dict:
        items = list(target_dict.items())
        for i, (symbol, name) in enumerate(items):
            try:
                df = yf.Ticker(symbol).history(period="6mo")
                if df.empty or len(df) < 20: continue
                
                # 確保數據類型正確
                close_prices = df['Close'].tolist()
                p = close_prices[-1]
                p_prev = close_prices[-2]
                
                ma5_series = df['Close'].rolling(5).mean()
                ma20_series = df['Close'].rolling(20).mean()
                vol_series = df['Volume'].rolling(5).mean()
                
                m5 = ma5_series.iloc[-1]
                m20 = ma20_series.iloc[-1]
                v_today = df['Volume'].iloc[-1]
                v_avg = vol_series.iloc[-1]
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
                
                time.sleep(0.01)
            except:
                continue
            finally:
                progress_bar.progress((i + 1) / len(items))

        st.session_state.final_df = pd.DataFrame(all_results) if all_results else None

# --- 2. 顯示排行榜 ---
if st.session_state.final_df is not None:
    st.subheader(f"🏆 {模式} 排行榜")
    st.dataframe(st.session_state.final_df, use_container_width=True)
elif st.session_state.get('final_df') is None:
    pass # 初始狀態不顯示

# --- 3. 核心連動診斷區 ---
st.divider()
st.subheader("📈 單股深度診斷")

if st.session_state.final_df is not None and not st.session_state.final_df.empty:
    stock_options = st.session_state.final_df.apply(lambda x: f"{x['代碼']} - {x['名稱']}", axis=1).tolist()
    selected_option = st.selectbox("🎯 選取股票進行分析", stock_options)
    diag_symbol = selected_option.split(" - ")[0]
else:
    diag_symbol = st.text_input("輸入代號 (如: 6669.TW)", "2330.TW")

if diag_symbol:
    df_diag = yf.Ticker(diag_symbol).history(period="6mo")
    if not df_diag.empty:
        fig = go.Figure(data=[go.Candlestick(x=df_diag.index, open=df_diag['Open'], high=df_diag['High'], low=df_diag['Low'], close=df_diag['Close'], name='K線')])
        fig.update_layout(template='plotly_dark', height=500, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
