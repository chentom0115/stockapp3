import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# 請在此處貼上您的永久 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoibGlvOTE5IiwiZW1haWwiOiJsaW85MTlAZ21haWwuY29tIn0.BUuQUOm9I528zgPhVvQOfOYDqS2fd5YudA6PKa1vHgA"

st.set_page_config(page_title="韭菜選股 V1 - 核心邏輯版", layout="wide")
st.title("🚀 韭菜選股 V1")

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 選股核心設定")
模式 = st.sidebar.radio("選擇操作模式", ["搶短爆發型 (看噴發)", "釣魚穩健型 (看回測)"])

# 1. 取得參數設定 (比照 .ipynb 邏輯)
if 模式 == "搶短爆發型 (看噴發)":
    change_threshold = st.sidebar.slider("今日最低漲幅 (%)", 1.0, 5.0, 2.0)
    vol_multiplier = st.sidebar.slider("量能爆發倍數", 1.0, 3.0, 1.5)
else:
    st.sidebar.markdown("---")
    st.sidebar.info("模式：價格高於 MA5 且 MA5 > MA20，尋找近三個月低檔區。")

target_group = st.sidebar.selectbox("3. 選擇魚池", ["電子股精選 (Top 150)", "AI 伺服器專區"])

if 'final_df' not in st.session_state:
    st.session_state.final_df = None

@st.cache_data(ttl=3600)
def get_stock_pool(group_name):
    dl = DataLoader()
    try:
        if FINMIND_TOKEN: dl.login(token=FINMIND_TOKEN)
        df_info = dl.taiwan_stock_info()
        # 產業過濾：比照筆記本邏輯
        keywords = '電子|半導體|光電|通訊|網通|資訊'
        elec_df = df_info[df_info['industry_category'].str.contains(keywords, na=False)]
        
        if group_name == "AI 伺服器專區":
            ai_list = ["2330", "2317", "2382", "3231", "6669", "3017", "2376"]
            elec_df = elec_df[elec_df['stock_id'].isin(ai_list)]
        
        res = {f"{row['stock_id']}{'.TW' if row['type']=='twse' else '.TWO'}": row['stock_name'] 
               for _, row in elec_df.head(150).iterrows()}
        res["6669.TW"] = "緯穎" # 確保緯穎必備
        return res
    except:
        return {"2330.TW": "台積電", "6669.TW": "緯穎"}

# --- 1. 執行掃描 (搬移 .ipynb 評分邏輯) ---
if st.sidebar.button("🚀 開始全自動掃描"):
    target_dict = get_stock_pool(target_group)
    all_results = []
    progress_bar = st.progress(0)
    
    items = list(target_dict.items())
    for i, (symbol, name) in enumerate(items):
        try:
            df = yf.Ticker(symbol).history(period="6mo")
            if df.empty or len(df) < 22: continue
            
            # 指標計算
            p = df['Close'].iloc[-1]
            p_prev = df['Close'].iloc[-2]
            ma5 = df['Close'].rolling(5).mean().iloc[-1]
            ma20 = df['Close'].rolling(20).mean().iloc[-1]
            v_today = df['Volume'].iloc[-1]
            v_avg = df['Volume'].rolling(5).mean().iloc[-1]
            high_3m = df['High'].tail(60).max()
            change = (p - p_prev) / p_prev * 100
            score = 0

            if 模式 == "搶短爆發型 (看噴發)":
                if p > ma5: score += 30
                if change > change_threshold: score += 30
                if v_today > v_avg * vol_multiplier: score += 40
                diag_msg = "🔥 動能噴發"
            else:
                # 釣魚穩健型
                if p > ma5 and ma5 > ma20: score += 40
                if v_today > v_avg: score += 30
                # 距離近三個月高點在 10% ~ 35% 之間視為低檔區
                dist_high = (high_3m - p) / high_3m * 100
                if 10 <= dist_high <= 35: score += 30
                diag_msg = "💎 回測支撐"

            if score >= 60:
                all_results.append({
                    "名稱": name, "代碼": symbol, "價格": round(p, 2), 
                    "得分": score, "漲幅%": f"{change:.2f}%", "診斷": diag_msg
                })
        except: continue
        finally:
            progress_bar.progress((i + 1) / len(items))

    if all_results:
        st.session_state.final_df = pd.DataFrame(all_results).sort_values(by="得分", ascending=False)
    else:
        st.session_state.final_df = None
        st.warning("目前沒有標的符合篩選條件。")

# --- 2. 顯示排行榜 ---
if st.session_state.final_df is not None:
    st.subheader(f"🏆 {模式} 得分排行榜")
    st.dataframe(st.session_state.final_df, use_container_width=True)

# --- 3. 核心連動診斷區 ---
st.divider()
st.subheader("📈 單股深度診斷 (自動連動)")
if st.session_state.final_df is not None and not st.session_state.final_df.empty:
    options = st.session_state.final_df.apply(lambda x: f"{x['代碼']} - {x['名稱']}", axis=1).tolist()
    selected = st.selectbox("🎯 選取診斷標的", options)
    diag_symbol = selected.split(" - ")[0]
else:
    diag_symbol = st.text_input("輸入代號診斷 (如: 6669.TW)", "6669.TW")

if diag_symbol:
    df_diag = yf.Ticker(diag_symbol).history(period="6mo")
    if not df_diag.empty:
        fig = go.Figure(data=[go.Candlestick(x=df_diag.index, open=df_diag['Open'], high=df_diag['High'], low=df_diag['Low'], close=df_diag['Close'])])
        fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['Close'].rolling(5).mean(), name='MA5', line=dict(color='orange', width=1)))
        fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['Close'].rolling(20).mean(), name='MA20', line=dict(color='blue', width=1)))
        fig.update_layout(template='plotly_dark', height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
