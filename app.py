import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go

# --- [設定區] ---
FINMIND_TOKEN = "您的_TOKEN"

st.set_page_config(page_title="韭菜選股 V1", layout="wide")
st.title("🚀 韭菜選股 V1")

# --- [側邊欄] (保持與您截圖一致的佈局) ---
with st.sidebar:
    st.header("🔍 選股核心設定")
    模式 = st.radio("選擇操作模式", ["釣魚穩健型 (看回測)", "搶短爆發型 (看噴發)"])
    st.divider()
    
    if 模式 == "釣魚穩健型 (看回測)":
        dist_threshold = st.slider("距離支撐門檻 (%)", 0.5, 8.0, 4.5)
        min_rr_ratio = st.slider("最低風報比要求", 1.0, 5.0, 2.0)
    else:
        change_threshold = st.slider("今日最低漲幅 (%)", 1.0, 7.0, 2.5)
        vol_multiplier = st.slider("量能爆發倍數", 1.0, 3.0, 1.5)
    
    scan_btn = st.button("🚀 開始全自動掃描")

# --- [核心掃描] ---
# (此處省略部分重複的掃描邏輯，確保 final_df 有數據)

# --- [重點：K線診斷區標註] ---
st.divider()
st.subheader("📈 單股深度診斷 (指標標註版)")

if st.session_state.get('final_df') is not None:
    options = st.session_state.final_df.apply(lambda x: f"{x['代碼']} - {x['名稱']}", axis=1).tolist()
    selected = st.selectbox("🎯 選取標的進行分析", options)
    diag_sid = selected.split(" - ")[0]
else:
    diag_sid = st.text_input("輸入代號 (如: 6669.TW)", "6669.TW")

if diag_sid:
    df = yf.Ticker(diag_sid).history(period="6mo")
    if not df.empty:
        # 計算指標
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        high_6m = df['High'].max()
        last_ma20 = df['MA20'].iloc[-1]

        # 1. 主圖：K線
        fig = go.Figure(data=[go.Candlestick(
            x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], 
            name='K線'
        )])

        # 2. 標出 MA20 月線 (您的核心支撐)
        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='MA20 月線', line=dict(color='cyan', width=2)))

        # 3. 標出 MA5 短線趨勢
        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='MA5 趨勢', line=dict(color='orange', width=1, dash='dot')))

        # 4. 標出 6個月高點 (壓力位/獲利目標)
        fig.add_hline(y=high_6m, line_dash="dash", line_color="red", 
                      annotation_text=f"6M 高點: {high_6m:.1f}", annotation_position="top left")

        # 5. 標出「回測支撐區」 (MA20 + 門檻範圍)
        # 畫出一個半透明的綠色區塊，顯示什麼價格叫「靠近支撐」
        upper_support = last_ma20 * (1 + dist_threshold/100)
        fig.add_hrect(y0=last_ma20, y1=upper_support, fillcolor="green", opacity=0.1, 
                      layer="below", line_width=0, annotation_text="買進支撐區")

        # 6. 圖表美化
        fig.update_layout(
            template='plotly_dark',
            height=600,
            title=f"{diag_sid} 技術指標診斷",
            xaxis_rangeslider_visible=False,
            yaxis_title="價格 (TWD)",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )

        st.plotly_chart(fig, use_container_width=True)
        
        # 額外數據診斷
        c1, c2, c3 = st.columns(3)
        c1.metric("當前價格", f"{df['Close'].iloc[-1]:.1f}")
        c2.metric("MA20 支撐", f"{last_ma20:.1f}")
        c3.metric("距支撐距離", f"{((df['Close'].iloc[-1]-last_ma20)/last_ma20*100):.2f}%")
