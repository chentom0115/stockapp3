import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# 設定 Token (建議將這行換成你截圖中的那串長代碼)
FINMIND_TOKEN = "你的_TOKEN_貼在這邊"

st.set_page_config(page_title="韭菜選股 V1 - 專業版", layout="wide")
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
    ["全部電子股 (Top 200 成交值)", "AI 伺服器/代工", "CPO 矽光子", "低軌衛星概念", "載板三雄"])

# 初始化 Session State
if 'final_df' not in st.session_state:
    st.session_state.final_df = None

# 使用 Cache 避免重複呼叫 API 浪費額度
@st.cache_data(ttl=3600)
def get_target_stocks(group_name):
    dl = DataLoader()
    dl.login(token=FINMIND_TOKEN) # 使用你的永久 Token 登入
    
    if group_name == "全部電子股 (Top 200 成交值)":
        # 1. 取得基本資訊
        df_info = dl.taiwan_stock_info()
        
        # 2. 取得今日成交排名 (這在有 Token 的情況下很穩定)
        # 嘗試抓取今日，若無則抓昨日
        for i in range(5):
            target_date = (datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d')
            try:
                # 這裡使用比較穩定的日平均價格接口來計算成交價值
                df_price = dl.taiwan_stock_day_avg_price(data_id="", start_date=target_date)
                if not df_price.empty: break
            except: continue
        
        if df_price.empty: return {}

        # 3. 合併並過濾電子股 (關鍵：加入電腦及週邊業)
        merged = pd.merge(df_price, df_info, on='stock_id')
        keywords = '電子|半導體|光電|電腦及週邊|通信網路'
        elec_all = merged[merged['industry_category'].str.contains(keywords, na=False)].copy()
        
        # 4. 排序成交金額 (成交量 * 均價)
        elec_all['turnover'] = elec_all['trade_quantity'] * elec_all['avg_price']
        top_df = elec_all.sort_values(by='turnover', ascending=False).head(200)
        
        # 轉為字典
        res = {f"{row['stock_id']}{'.TW' if row['type']=='twse' else '.TWO'}": row['stock_name'] for _, row in top_df.iterrows()}
        
        # 再次確認緯穎是否存在，不存在則手動插入 (雙重保險)
        if "6669.TW" not in res: res["6669.TW"] = "緯穎"
        return res
    else:
        # 手動定義的小魚池
        groups = {
            "AI 伺服器/代工": {"2330.TW": "台積電", "2317.TW": "鴻海", "2382.TW": "廣達", "3231.TW": "緯創", "6669.TW": "緯穎", "3017.TW": "奇鋐", "2376.TW": "技嘉"},
            "CPO 矽光子": {"3665.TW": "貿聯-KY", "6442.TW": "光聖", "3081.TW": "聯亞", "3363.TWO": "上詮", "3163.TWO": "波若威", "4979.TWO": "華星光"},
            "低軌衛星概念": {"2313.TW": "華通", "2314.TW": "台揚", "3491.TWO": "昇達科", "6274.TWO": "台燿", "2383.TW": "台光電"},
            "載板三雄": {"3037.TW": "欣興", "8046.TW": "南電", "3189.TW": "景碩", "2368.TW": "金像電"}
        }
        return groups.get(group_name, {})

# --- 1. 執行掃描 ---
if st.sidebar.button("🚀 開始全自動掃描"):
    target_dict = get_target_stocks(target_group)
    all_results = []
    progress_bar = st.progress(0)
    
    if not target_dict:
        st.error("無法取得魚池清單，請檢查 Token 或網路。")
    else:
        items = list(target_dict.items())
        for i, (symbol, name) in enumerate(items):
            try:
                df = yf.Ticker(symbol).history(period="6mo")
                if df.empty or len(df) < 22: continue
                
                # 數值計算
                p = df['Close'].iloc[-1].item()
                p_prev = df['Close'].iloc[-2].item()
                m5 = df['Close'].rolling(5).mean().iloc[-1].item()
                m20 = df['Close'].rolling(20).mean().iloc[-1].item()
                v_today = df['Volume'].iloc[-1].item()
                v_avg = df['Volume'].rolling(5).mean().iloc[-1].item()
                high_6mo = df['High'].max().item()
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
                
                time.sleep(0.01) # 有 Token 後可以加快速度
            except: continue
            finally:
                progress_bar.progress((i + 1) / len(items))

        st.session_state.final_df = pd.DataFrame(all_results) if all_results else None

# --- 2. 顯示排行榜 ---
if st.session_state.final_df is not None:
    st.subheader(f"🏆 {模式} 排行榜")
    st.dataframe(st.session_state.final_df, use_container_width=True)

# --- 3. 核心連動診斷區 ---
st.divider()
st.subheader("📈 單股深度診斷 (自動連動排行榜)")

if st.session_state.final_df is not None and not st.session_state.final_df.empty:
    stock_options = st.session_state.final_df.apply(lambda x: f"{x['代碼']} - {x['名稱']}", axis=1).tolist()
    selected_option = st.selectbox("🎯 選取股票", stock_options)
    diag_symbol = selected_option.split(" - ")[0]
else:
    diag_symbol = st.text_input("輸入代號 (如: 6669.TW)", "2330.TW")

if diag_symbol:
    df_diag = yf.Ticker(diag_symbol).history(period="6mo")
    if not df_diag.empty:
        fig = go.Figure(data=[go.Candlestick(x=df_diag.index, open=df_diag['Open'], high=df_diag['High'], low=df_diag['Low'], close=df_diag['Close'], name='K線')])
        fig.update_layout(template='plotly_dark', height=500, margin=dict(l=10, r=10, t=10, b=10), xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
