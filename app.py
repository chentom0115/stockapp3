import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
import time

st.set_page_config(page_title="韭菜選股 V1", layout="wide")
st.title("🧬 韭菜選股 V1)

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
    ["全部電子股 (Top 200)", "AI 伺服器/代工", "CPO 矽光子", "低軌衛星概念", "載板三雄"])

if 'final_df' not in st.session_state:
    st.session_state.final_df = None

# --- 執行按鈕 ---
if st.sidebar.button("🚀 開始全自動掃描"):
    groups = {
        "AI 伺服器/代工": {"2330.TW": "台積電", "2317.TW": "鴻海", "2382.TW": "廣達", "3231.TW": "緯創", "6669.TW": "緯穎", "3017.TW": "奇鋐"},
        "CPO 矽光子": {"3665.TW": "貿聯-KY", "6442.TW": "光聖", "3081.TW": "聯亞", "3363.TWO": "上詮", "3163.TWO": "波若威", "4979.TWO": "華星光"},
        "低軌衛星概念": {"2313.TW": "華通", "2314.TW": "台揚", "3491.TWO": "昇達科", "6274.TWO": "台燿", "2383.TW": "台光電"},
        "載板三雄": {"3037.TW": "欣興", "8046.TW": "南電", "3189.TW": "景碩", "2368.TW": "金像電"}
    }
    
    all_results = []
    if target_group == "全部電子股 (Top 200)":
        dl = DataLoader()
        df_info = dl.taiwan_stock_info()
        elec_df = df_info[df_info['industry_category'].str.contains('電子|半導體|光電', na=False)]
        target_dict = {f"{row['stock_id']}.TW": row['stock_name'] for _, row in elec_df.head(200).iterrows()}
    else:
        target_dict = groups[target_group]
    
    progress_bar = st.progress(0)
    for i, (symbol, name) in enumerate(target_dict.items()):
        try:
            df = yf.Ticker(symbol).history(period="6mo")
            if df.empty: df = yf.Ticker(symbol.replace(".TW", ".TWO")).history(period="6mo")
            if len(df) < 22: continue
            
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

# --- 顯示結果與分析助手 ---
if st.session_state.final_df is not None:
    st.subheader(f"🏆 {模式} 排行榜")
    st.dataframe(st.session_state.final_df, use_container_width=True)
    if st.button("🤖 生成 AI 盤後分析指令"):
        top_data = st.session_state.final_df.head(3).to_string(index=False)
        st.code(f"請分析以下數據並給予建議：\n{top_data}", language="text")

# --- 🚀 下方新增：單股深度診斷 K 線圖區 ---
st.divider()
st.subheader("📈 單股深度診斷 (K 線儀表板)")
diag_symbol = st.text_input("輸入要診斷的股票代號 (例如: 2330.TW 或 3081.TWO)", "2330.TW")

if diag_symbol:
    df_diag = yf.Ticker(diag_symbol).history(period="6mo")
    if not df_diag.empty:
        df_diag['MA5'] = df_diag['Close'].rolling(5).mean()
        df_diag['MA20'] = df_diag['Close'].rolling(20).mean()
        df_diag['MA60'] = df_diag['Close'].rolling(60).mean()
        
        # 買進訊號 (由下往上穿過 MA5)
        buy_signal = (df_diag['Close'] > df_diag['MA5']) & (df_diag['Close'].shift(1) < df_diag['MA5'].shift(1))
        
        fig = go.Figure(data=[go.Candlestick(x=df_diag.index, open=df_diag['Open'], high=df_diag['High'], low=df_diag['Low'], close=df_diag['Close'], name='K線')])
        fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['MA5'], line=dict(color='orange', width=1), name='MA5'))
        fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['MA20'], line=dict(color='blue', width=1), name='MA20'))
        fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['MA60'], line=dict(color='red', width=1.5, dash='dot'), name='MA60 (季線)'))
        fig.add_trace(go.Scatter(x=df_diag[buy_signal].index, y=df_diag[buy_signal]['Low'] * 0.98, mode='markers', marker=dict(symbol='triangle-up', size=12, color='lime'), name='起漲訊號'))
        
        fig.update_layout(template='plotly_dark', height=500, margin=dict(l=20, r=20, t=20, b=20))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.error("找不到該代號數據，請確認格式是否正確。")
