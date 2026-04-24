import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
import time

st.set_page_config(page_title="韭菜選股 V1", layout="wide")
st.title(" 韭菜選股 V1")

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
    ["全部電子股 (Top 100)", "AI 伺服器/代工", "CPO 矽光子", "低軌衛星概念", "載板三雄"])

# 初始化 Session State
if 'final_df' not in st.session_state:
    st.session_state.final_df = None

# --- 1. 執行掃描 ---
if st.sidebar.button("🚀 開始全自動掃描"):
    groups = {
        "AI 伺服器/代工": {"2330.TW": "台積電", "2317.TW": "鴻海", "2382.TW": "廣達", "3231.TW": "緯創", "6669.TW": "緯穎", "3017.TW": "奇鋐"},
        "CPO 矽光子": {"3665.TW": "貿聯-KY", "6442.TW": "光聖", "3081.TW": "聯亞", "3363.TWO": "上詮", "3163.TWO": "波若威", "4979.TWO": "華星光"},
        "低軌衛星概念": {"2313.TW": "華通", "2314.TW": "台揚", "3491.TWO": "昇達科", "6274.TWO": "台燿", "2383.TW": "台光電"},
        "載板三雄": {"3037.TW": "欣興", "8046.TW": "南電", "3189.TW": "景碩", "2368.TW": "金像電"}
    }
    all_results = []
    if target_group == "全部電子股 (Top 100)":
        dl = DataLoader()
        
        # 1. 取得當日股票交易統計 (這是在 FinMind 最穩定的 API 之一)
        # 我們抓最近一個交易日的資料
        today_str = pd.Timestamp.now().strftime('%Y-%m-%d')
        df_price = dl.taiwan_stock_day_avg_price(data_id="", start_date=today_str)
        
        # 如果沒資料（週末或還沒收盤），往前推幾天
        if df_price.empty:
            df_price = dl.taiwan_stock_day_avg_price(data_id="", start_date=(pd.Timestamp.now() - pd.Timedelta(days=5)).strftime('%Y-%m-%d'))

        # 2. 取得產業分類資訊
        df_info = dl.taiwan_stock_info()
        
        # 3. 合併並過濾產業
        merged_df = pd.merge(df_price, df_info, on='stock_id')
        keywords = '電子|半導體|光電|電腦及週邊|通信網路'
        elec_all = merged_df[merged_df['industry_category'].str.contains(keywords, na=False)]
        
        # 4. 關鍵：手動計算「成交價值」並排序
        # 成交金額 = 成交量 (trade_quantity) * 平均價 (avg_price)
        # 注意：不同 API 欄位名可能略有不同，這裡確保安全
        if 'trade_quantity' in elec_all.columns:
            elec_all['turnover'] = elec_all['trade_quantity'] * elec_all['avg_price']
            # 取成交值前 150 名（確保緯穎一定在內）
            elec_top = elec_all.sort_values(by='turnover', ascending=False).head(150)
        else:
            # 如果抓不到成交量欄位，就退而求其次抓前 150 支股票（至少比 head(100) 多）
            elec_top = elec_all.head(150)

        target_dict = {f"{row['stock_id']}.TW": row['stock_name'] for _, row in elec_top.iterrows()}
    
    progress_bar = st.progress(0)
    for i, (symbol, name) in enumerate(target_dict.items()):
        try:
            df = yf.Ticker(symbol).history(period="6mo")
            if df.empty:
                symbol = symbol.replace(".TW", ".TWO")
                df = yf.Ticker(symbol).history(period="6mo")
            if df.empty or len(df) < 22: continue
            
            p = df['Close'].iloc[-1].item()
            m5 = df['Close'].rolling(5).mean().iloc[-1].item()
            m20 = df['Close'].rolling(20).mean().iloc[-1].item()
            v_today = df['Volume'].iloc[-1].item()
            v_avg = df['Volume'].rolling(5).mean().iloc[-1].item()
            high_6mo = df['High'].max().item()
            change = (p - df['Close'].iloc[-2].item()) / df['Close'].iloc[-2].item() * 100

            if "釣魚" in 模式:
                dist_20 = (p - m20) / m20 * 100
                if 0 <= dist_20 <= dist_threshold:
                    reward = high_6mo - p
                    risk = p - (m20 * 0.98)
                    ratio = round(reward / risk, 2) if risk > 0 else 0
                    if ratio >= min_rr_ratio:
                        all_results.append({"名稱": name, "代碼": symbol, "價格": round(p, 2), "風報比": ratio, "診斷": "回測支撐"})
            else:
                if change >= change_threshold and v_today >= v_avg * vol_multiplier and p > m5:
                    all_results.append({"名稱": name, "代碼": symbol, "價格": round(p, 2), "漲幅%": f"{change:.2f}%", "診斷": "🔥動能噴發"})
            time.sleep(0.05)
        except: continue
        progress_bar.progress((i + 1) / len(target_dict))
    st.session_state.final_df = pd.DataFrame(all_results) if all_results else None

# --- 2. 顯示排行榜 ---
if st.session_state.final_df is not None:
    st.subheader(f"🏆 {模式} 排行榜")
    st.dataframe(st.session_state.final_df, use_container_width=True)

# --- 3. 核心連動診斷區 ---
st.divider()
st.subheader("📈 單股深度診斷 (自動連動排行榜)")

# 建立下拉選單：如果有排行榜，就把代碼放進去；如果沒有，預設為台積電
if st.session_state.final_df is not None and not st.session_state.final_df.empty:
    # 建立一個方便閱讀的格式，例如：2330.TW - 台積電
    stock_options = st.session_state.final_df.apply(lambda x: f"{x['代碼']} - {x['名稱']}", axis=1).tolist()
    selected_option = st.selectbox("🎯 請從排行榜中選取要診斷的股票", stock_options)
    diag_symbol = selected_option.split(" - ")[0] # 抓出前方的代碼
else:
    diag_symbol = st.text_input("輸入要診斷的股票代號", "2330.TW")

# 繪製圖表 (同前，但自動抓取 diag_symbol)
if diag_symbol:
    df_diag = yf.Ticker(diag_symbol).history(period="6mo")
    if not df_diag.empty:
        df_diag['MA5'] = df_diag['Close'].rolling(5).mean()
        df_diag['MA20'] = df_diag['Close'].rolling(20).mean()
        df_diag['MA60'] = df_diag['Close'].rolling(60).mean()
        buy_signal = (df_diag['Close'] > df_diag['MA5']) & (df_diag['Close'].shift(1) < df_diag['MA5'].shift(1))
        
        fig = go.Figure(data=[go.Candlestick(x=df_diag.index, open=df_diag['Open'], high=df_diag['High'], low=df_diag['Low'], close=df_diag['Close'], name='K線')])
        fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['MA5'], line=dict(color='orange', width=1), name='MA5'))
        fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['MA20'], line=dict(color='blue', width=1), name='MA20'))
        fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['MA60'], line=dict(color='red', width=1.5, dash='dot'), name='MA60'))
        fig.add_trace(go.Scatter(x=df_diag[buy_signal].index, y=df_diag[buy_signal]['Low'] * 0.98, mode='markers', marker=dict(symbol='triangle-up', size=12, color='lime'), name='起漲訊號'))
        fig.update_layout(template='plotly_dark', height=500, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
