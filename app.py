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
                
                time.sleep(0.02)
            except:
                continue
            finally:
                count += 1
                progress_bar.progress(count / total)

        st.session_state.final_df = pd.DataFrame(all_results) if all_results else None

# --- 2. 顯示排行榜 ---
if st.session_state.final_df is not None:
    # 修正原本噴發錯誤的地方：加上閉合括號
    st.subheader(f"🏆 {模式} 排行榜")
    st.dataframe(st.session_state.final_df, use_container_width=True)
elif st.session_state.final_df is None and 'final_df' in st.session_state:
    st.info("掃描完成，但目前沒有符合篩選條件的標的。")

# --- 3. 核心連動診斷區 ---
st.divider()
st.subheader("📈 單股深度診斷 (自動連動排行榜)")

if st.session_state.final_df is not None and not st.session_state.final_df.empty:
    stock_options = st.session_state.final_df.apply(lambda x: f"{x['代碼']} - {x['名稱']}", axis=1).tolist()
    selected_option = st.selectbox("🎯 請從排行榜中選取要診斷的股票", stock_options)
    diag_symbol = selected_option.split(" - ")[0]
else:
    diag_symbol = st.text_input("輸入要診斷的股票代號 (例如: 6669.TW)", "2330.TW")

if diag_symbol:
    with st.spinner(f"正在載入 {diag_symbol} 技術圖表..."):
        try:
            df_diag = yf.Ticker(diag_symbol).history(period="6mo")
            if not df_diag.empty:
                df_diag['MA5'] = df_diag['Close'].rolling(5).mean()
                df_diag['MA20'] = df_diag['Close'].rolling(20).mean()
                df_diag['MA60'] = df_diag['Close'].rolling(60).mean()
                buy_signal = (df_diag['Close'] > df_diag['MA5']) & (df_diag['Close'].shift(1) < df_diag['MA5'].shift(1))
                
                fig = go.Figure(data=[go.Candlestick(
                    x=df_diag.index, open=df_diag['Open'], high=df_diag['High'],
                    low=df_diag['Low'], close=df_diag['Close'], name='K線')])
                
                fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['MA5'], line=dict(color='orange', width=1), name='MA5'))
                fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['MA20'], line=dict(color='cyan', width=1), name='MA20'))
                fig.add_trace(go.Scatter(x=df_diag.index, y=df_diag['MA60'], line=dict(color='red', width=1.5, dash='dot'), name='MA60'))
                
                fig.add_trace(go.Scatter(
                    x=df_diag[buy_signal].index, y=df_diag[buy_signal]['Low'] * 0.97, 
                    mode='markers', marker=dict(symbol='triangle-up', size=12, color='lime'), name='起漲訊號'))
                
                fig.update_layout(template='plotly_dark', height=600, 
                                  margin=dict(l=10, r=10, t=10, b=10),
                                  xaxis_rangeslider_visible=False)
                st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.error(f"圖表繪製發生錯誤: {e}")
