import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# 請在此貼入您的 FinMind Token
FINMIND_TOKEN = "您的_TOKEN"

st.set_page_config(page_title="韭菜選股 V1 - 專業版", layout="wide")
st.title("🚀 韭菜選股 V1")

# --- 側邊欄：參數設定區 (對齊截圖佈局) ---
with st.sidebar:
    st.header("🔍 選股核心設定")
    模式 = st.radio("選擇操作模式", ["搶短爆發型 (看噴發)", "釣魚穩健型 (看回測)"])
    st.divider()
    
    if 模式 == "搶短爆發型 (看噴發)":
        change_threshold = st.slider("今日最低漲幅 (%)", 1.0, 7.0, 2.5)
        vol_multiplier = st.slider("量能爆發倍數", 1.0, 3.0, 1.5)
    else:
        dist_threshold = st.slider("距離支撐門檻 (%)", 0.5, 8.0, 4.5)
        min_rr_ratio = st.slider("最低風報比要求", 1.0, 5.0, 2.0)
    
    target_group = st.selectbox("3. 選擇魚池", ["AI 伺服器/代工", "全部電子股 (Top 100)", "CPO 矽光子"])
    scan_btn = st.button("🚀 開始全自動掃描")

# --- 工具函數：獲取魚池清單 (Cache 優化) ---
@st.cache_data(ttl=3600)
def get_stock_pool(group):
    dl = DataLoader()
    try:
        if FINMIND_TOKEN: dl.login(token=FINMIND_TOKEN)
        df_info = dl.taiwan_stock_info()
        if group == "AI 伺服器/代工":
            codes = ["2330", "2317", "2382", "3231", "6669", "3017", "2376"]
            return {f"{c}.TW": df_info[df_info['stock_id']==c]['stock_name'].values[0] for c in codes}
        # 預設過濾電子相關產業
        keywords = '電子|半導體|電腦|通信|光電'
        elec_df = df_info[df_info['industry_category'].str.contains(keywords, na=False)]
        res = {f"{r['stock_id']}{'.TW' if r['type']=='twse' else '.TWO'}": r['stock_name'] for _, r in elec_df.head(100).iterrows()}
        res["6669.TW"] = "緯穎"
        return res
    except:
        return {"6669.TW": "緯穎", "2330.TW": "台積電"}

# --- 1. 核心掃描與評分邏輯 (搬移 .ipynb) ---
if scan_btn:
    target_dict = get_stock_pool(target_group)
    all_results = []
    progress_bar = st.progress(0)
    
    items = list(target_dict.items())
    for i, (symbol, name) in enumerate(items):
        try:
            df = yf.Ticker(symbol).history(period="6mo")
            if df.empty or len(df) < 22: continue
            
            p = df['Close'].iloc[-1]
            p_prev = df['Close'].iloc[-2]
            ma5 = df['Close'].rolling(5).mean().iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            v_today = df['Volume'].iloc[-1]
            v_avg = df['Volume'].rolling(5).mean().iloc[-1]
            high_6m = df['High'].max()
            change = (p - p_prev) / p_prev * 100
            score = 0

            if 模式 == "搶短爆發型 (看噴發)":
                if p > ma5: score += 30
                if change >= change_threshold: score += 30
                if v_today >= v_avg * vol_multiplier: score += 40
                if score >= 60:
                    all_results.append({"名稱": name, "代碼": symbol, "價格": round(p, 1), "得分": score, "漲幅%": f"{change:.2f}%", "診斷": "🔥 動能噴發"})
            else:
                # 釣魚穩健型：對齊截圖中的風報比邏輯
                dist_20 = (p - ma20) / ma20 * 100
                if 0 <= dist_20 <= dist_threshold:
                    reward = high_6m - p
                    risk = p - (ma20 * 0.98)
                    rr = round(reward / risk, 2) if risk > 0 else 0
                    if rr >= min_rr_ratio:
                        all_results.append({"名稱": name, "代碼": symbol, "價格": round(p, 1), "風報比": rr, "得分": int(rr*20), "診斷": "💎 回測支撐"})
        except: continue
        progress_bar.progress((i + 1) / len(items))
    
    st.session_state.final_df = pd.DataFrame(all_results).sort_values(by="得分", ascending=False) if all_results else None

# --- 2. 顯示結果排行榜 ---
if st.session_state.get('final_df') is not None:
    st.subheader(f"🏆 {模式} 排行榜")
    st.dataframe(st.session_state.final_df, use_container_width=True)

# --- 3. 單股深度診斷區 (對齊最新截圖佈局) ---
st.divider()
st.subheader("📈 單股深度診斷 (自動連動)")

if st.session_state.get('final_df') is not None and not st.session_state.final_df.empty:
    options = st.session_state.final_df.apply(lambda x: f"{x['代碼']} - {x['名稱']}", axis=1).tolist()
    selected = st.selectbox("🎯 請從排行榜中選取標的", options)
    diag_sid = selected.split(" - ")[0]
else:
    diag_sid = st.text_input("手動輸入代號 (如: 6669.TW)", "6669.TW")

if diag_sid:
    with st.spinner("載入圖表中..."):
        df_diag = yf.Ticker(diag_sid).history(period="6mo")
        if not df_diag.empty:
            # === 計算均線 ===
df_diag['MA5'] = df_diag['Close'].rolling(5).mean()
df_diag['MA20'] = df_diag['Close'].rolling(20).mean()
df_diag['MA60'] = df_diag['Close'].rolling(60).mean()

# === 起漲訊號（條件你可再優化）===
# 條件：站上MA5 + MA5 > MA20 + 量能放大
df_diag['vol_avg'] = df_diag['Volume'].rolling(5).mean()
df_diag['signal'] = (
    (df_diag['Close'] > df_diag['MA5']) &
    (df_diag['MA5'] > df_diag['MA20']) &
    (df_diag['Volume'] > df_diag['vol_avg'] * 1.2)
)

signal_df = df_diag[df_diag['signal']]

# === 建立圖表（上下兩層）===
from plotly.subplots import make_subplots

fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.03,
    row_heights=[0.7, 0.3]
)

# === K線 ===
fig.add_trace(go.Candlestick(
    x=df_diag.index,
    open=df_diag['Open'],
    high=df_diag['High'],
    low=df_diag['Low'],
    close=df_diag['Close'],
    name='K線'
), row=1, col=1)

# === 均線 ===
fig.add_trace(go.Scatter(
    x=df_diag.index, y=df_diag['MA5'],
    name='MA5',
    line=dict(color='yellow', width=2)
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df_diag.index, y=df_diag['MA20'],
    name='MA20',
    line=dict(color='blue', width=2)
), row=1, col=1)

fig.add_trace(go.Scatter(
    x=df_diag.index, y=df_diag['MA60'],
    name='MA60 (季線)',
    line=dict(color='red', width=2, dash='dot')
), row=1, col=1)

# === 起漲三角形 ===
fig.add_trace(go.Scatter(
    x=signal_df.index,
    y=signal_df['Low'] * 0.98,
    mode='markers',
    name='起漲訊號',
    marker=dict(
        symbol='triangle-up',
        color='lime',
        size=10
    )
), row=1, col=1)

# === 成交量 ===
fig.add_trace(go.Bar(
    x=df_diag.index,
    y=df_diag['Volume'],
    name='Volume'
), row=2, col=1)

# === Layout ===
fig.update_layout(
    template='plotly_dark',
    height=600,
    margin=dict(l=10, r=10, t=30, b=10),
    xaxis_rangeslider_visible=False,
    legend=dict(
        orientation="v",
        x=1,
        y=1
    )
)

st.plotly_chart(fig, use_container_width=True)
