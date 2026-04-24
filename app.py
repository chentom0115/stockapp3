import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta

# 請在此處貼上你截圖中的永久 Token
FINMIND_TOKEN = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoibGlvOTE5IiwiZW1haWwiOiJsaW85MTlAZ21haWwuY29tIn0.BUuQUOm9I528zgPhVvQOfOYDqS2fd5YudA6PKa1vHgA"

st.set_page_config(page_title="韭菜選股 V1 - 穩定版", layout="wide")
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
    ["全部電子股 (Top 200)", "AI 伺服器/代工", "CPO 矽光子", "低軌衛星概念", "載板三雄"])

if 'final_df' not in st.session_state:
    st.session_state.final_df = None

# 使用 Cache 緩存資料，減少 API 呼叫壓力
@st.cache_data(ttl=3600)
def get_target_stocks(group_name):
    dl = DataLoader()
    # 修正：增加錯誤處理，若登入失敗則以匿名身分繼續（額度較少但不會崩潰）
    try:
        if FINMIND_TOKEN and FINMIND_TOKEN != "你的_TOKEN_字串":
            dl.login(token=FINMIND_TOKEN)
    except Exception as e:
        st.warning(f"Token 登入失敗，將以匿名模式執行: {e}")
    
    if group_name == "全部電子股 (Top 200)":
        try:
            df_info = dl.taiwan_stock_info()
            # 抓取最近 3 天的資料
            start_dt = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
            # 改用最基礎的價格介面獲取名單
            df_price = dl.taiwan_stock_day_avg_price(data_id="", start_date=start_dt)
            
            if not df_price.empty:
                last_date = df_price['date'].max()
                df_latest = df_price[df_price['date'] == last_date].copy()
                merged = pd.merge(df_latest, df_info, on='stock_id')
                
                # 產業過濾：確保包含電腦及週邊、半導體等
                keywords = '電子|半導體|光電|電腦及週邊|通信網路'
                elec_all = merged[merged['industry_category'].str.contains(keywords, na=False)].copy()
                
                # 計算成交值並排序
                elec_all['turnover'] = elec_all['trade_quantity'] * elec_all['avg_price']
                top_df = elec_all.sort_values(by='turnover', ascending=False).head(200)
                
                res = {f"{row['stock_id']}{'.TW' if row['type']=='twse' else '.TWO'}": row['stock_name'] for _, row in top_df.iterrows()}
                if "6669.TW" not in res: res["6669.TW"] = "緯穎"
                return res
        except Exception as e:
            st.error(f"獲取電子股名單出錯: {e}")
            return {"2330.TW": "台積電", "6669.TW": "緯穎"} # 失敗時的備援名單
    else:
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
    
    if target_dict:
        items = list(target_dict.items())
        for i, (symbol, name) in enumerate(items):
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
                
                time.sleep(0.01)
            except: continue
            finally:
                progress_bar.progress((i + 1) / len(items))

        st.session_state.final_df = pd.DataFrame(all_results) if all_results else None

# --- 2. 顯示排行榜 ---
if st.session_state.final_df is not None:
    st.subheader(f"🏆 {模式} 排行榜")
    st.dataframe(st.session_state.final_df, use_container_width=True)

# --- 3. 深度診斷 ---
st.divider()
if st.session_state.final_df is not None and not st.session_state.final_df.empty:
    stock_options = st.session_state.final_df.apply(lambda x: f"{x['代碼']} - {x['名稱']}", axis=1).tolist()
    selected = st.selectbox("🎯 選取診斷標的", stock_options)
    diag_symbol = selected.split(" - ")[0]
    
    df_diag = yf.Ticker(diag_symbol).history(period="6mo")
    if not df_diag.empty:
        fig = go.Figure(data=[go.Candlestick(x=df_diag.index, open=df_diag['Open'], high=df_diag['High'], low=df_diag['Low'], close=df_diag['Close'])])
        fig.update_layout(template='plotly_dark', height=500, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)
