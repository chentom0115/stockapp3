import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go

# --- [標註 1]：FinMind Token 登入 ---
# 這裡對齊您的永久 Token，確保 API 額度充足
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoibGlvOTE5IiwiZW1haWwiOiJsaW85MTlAZ21haWwuY29tIn0.BUuQUOm9I528zgPhVvQOfOYDqS2fd5YudA6PKa1vHgA"

st.set_page_config(page_title="韭菜選股 V1", layout="wide")
st.title("🚀 韭菜選股 V1")

# --- [標註 2]：側邊欄參數 (比照您截圖中的 UI 佈局) ---
with st.sidebar:
    st.header("🔍 選股核心設定")
    模式 = st.radio("選擇操作模式", ["搶短爆發型 (看噴發)", "釣魚穩健型 (看回測)"])
    st.divider()
    
    if 模式 == "搶短爆發型 (看噴發)":
        # 對齊 .ipynb 中的「動能轉強」與「量能噴發」門檻
        change_threshold = st.slider("今日最低漲幅 (%)", 1.0, 7.0, 2.5)
        vol_multiplier = st.slider("量能爆發倍數", 1.0, 3.0, 1.5)
    else:
        # 對齊 .ipynb 中的「回測支撐」與「獲利空間」門檻
        dist_threshold = st.slider("距離支撐門檻 (%)", 0.5, 8.0, 4.5)
        min_rr_ratio = st.slider("最低風報比要求", 1.0, 5.0, 2.0)
    
    target_group = st.selectbox("3. 選擇魚池", ["AI 伺服器/代工", "全部電子股 (Top 100)"])
    scan_btn = st.button("🚀 開始全自動掃描")

# --- [標註 3]：魚池過濾 (對齊 .ipynb 的電子產業關鍵字) ---
@st.cache_data(ttl=3600)
def get_stock_pool(group):
    dl = DataLoader()
    try:
        if FINMIND_TOKEN: dl.login(token=FINMIND_TOKEN)
        df_info = dl.taiwan_stock_info()
        # 精準對齊您筆記本中的產業過濾條件
        keywords = '電子|半導體|光電|通訊|網通|資訊|電腦及週邊'
        elec_df = df_info[df_info['industry_category'].str.contains(keywords, na=False)]
        
        if group == "AI 伺服器/代工":
            # 強制鎖定您最關注的 AI 龍頭股 (含緯穎 6669)
            ai_list = ["2330", "2317", "2382", "3231", "6669", "3017", "2376"]
            elec_df = elec_df[elec_df['stock_id'].isin(ai_list)]
            
        res = {f"{r['stock_id']}{'.TW' if r['type']=='twse' else '.TWO'}": r['stock_name'] for _, r in elec_df.head(100).iterrows()}
        return res
    except:
        return {"6669.TW": "緯穎", "2330.TW": "台積電"}

# --- [標註 4]：核心運算邏輯 (對齊 .ipynb 的評分與風報比公式) ---
if scan_btn:
    target_dict = get_stock_pool(target_group)
    all_results = []
    progress_bar = st.progress(0)
    
    items = list(target_dict.items())
    for i, (symbol, name) in enumerate(items):
        try:
            df = yf.Ticker(symbol).history(period="6mo")
            if df.empty or len(df) < 22: continue
            
            # 技術指標計算
            p = df['Close'].iloc[-1]           # 收盤價
            ma5 = df['Close'].rolling(5).mean().iloc[-1]   # 5MA
            ma20 = df['Close'].rolling(20).mean().iloc[-1] # 20MA (月線支撐)
            v_today = df['Volume'].iloc[-1]    # 今日成交量
            v_avg = df['Volume'].rolling(5).mean().iloc[-1] # 5日均量
            high_6m = df['High'].max()         # 六個月高點 (目標價參考)
            change = ((p - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100

            if 模式 == "搶短爆發型 (看噴發)":
                # 筆記本邏輯：收盤 > MA5 且 漲幅 > 門檻 且 量 > 均量 * 倍數
                if p > ma5 and change >= change_threshold and v_today >= v_avg * vol_multiplier:
                    all_results.append({"名稱": name, "代碼": symbol, "價格": round(p, 1), "漲幅%": f"{change:.2f}%", "診斷": "🔥 動能噴發"})
            else:
                # 筆記本邏輯：回測 MA20 支撐 且 計算風報比
                dist_20 = (p - ma20) / ma20 * 100
                if 0 <= dist_20 <= dist_threshold:
                    reward = high_6m - p        # 潛在獲利 (距離前高)
                    risk = p - (ma20 * 0.98)    # 潛在風險 (破月線停損)
                    rr = round(reward / risk, 2) if risk > 0 else 0
                    if rr >= min_rr_ratio:
                        all_results.append({"名稱": name, "代碼": symbol, "價格": round(p, 1), "風報比": rr, "診斷": "💎 回測支撐"})
        except: continue
        progress_bar.progress((i + 1) / len(items))
    
    st.session_state.final_df = pd.DataFrame(all_results)

# --- [標註 5]：排行與連動診斷 (對齊截圖佈局) ---
if st.session_state.get('final_df') is not None:
    st.subheader(f"🏆 {模式} 排行榜")
    st.dataframe(st.session_state.final_df, use_container_width=True)

st.divider()
st.subheader("📈 單股深度診斷")
if st.session_state.get('final_df') is not None and not st.session_state.final_df.empty:
    options = st.session_state.final_df.apply(lambda x: f"{x['代碼']} - {x['名稱']}", axis=1).tolist()
    selected = st.selectbox("🎯 選取標的", options)
    diag_sid = selected.split(" - ")[0]
    
    df_diag = yf.Ticker(diag_sid).history(period="6mo")
    fig = go.Figure(data=[go.Candlestick(x=df_diag.index, open=df_diag['Open'], high=df_diag['High'], low=df_diag['Low'], close=df_diag['Close'], name='K線')])
    fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['Close'].rolling(20).mean(), name='月線支撐', line=dict(color='cyan', width=1.5)))
    fig.update_layout(template='plotly_dark', height=500, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)
