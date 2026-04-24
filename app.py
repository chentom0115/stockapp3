import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import time

# 網頁基本設定
st.set_page_config(page_title="韭菜選股 V1", layout="wide")
st.title("🧬 韭菜選股 V1")

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 核心參數調校")

# 這裡就是您截圖中的兩個可調參數
dist_threshold = st.sidebar.slider("1. 距離支撐門檻 (%)", 0.5, 8.0, 4.5, step=0.5)
min_rr_ratio = st.sidebar.slider("2. 最低風報比要求", 1.0, 5.0, 2.0, step=0.5)

target_group = st.sidebar.selectbox("3. 選擇魚池", 
    ["全部電子股 (Top 150)", "AI 伺服器/代工", "CPO 矽光子", "低軌衛星概念", "載板三雄"])

# 定義固定族群
groups = {
    "AI 伺服器/代工": {"2330.TW": "台積電", "2317.TW": "鴻海", "2382.TW": "廣達", "3231.TW": "緯創", "6669.TW": "緯穎", "3017.TW": "奇鋐"},
    "CPO 矽光子": {"3665.TW": "貿聯-KY", "6442.TW": "光聖", "3081.TW": "聯亞", "3363.TWO": "上詮", "3163.TWO": "波若威", "4979.TWO": "華星光"},
    "低軌衛星概念": {"2313.TW": "華通", "2314.TW": "台揚", "3491.TWO": "昇達科", "6274.TWO": "台燿", "2383.TW": "台光電"},
    "載板三雄": {"3037.TW": "欣興", "8046.TW": "南電", "3189.TW": "景碩", "2368.TW": "金像電"}
}

# --- 執行按鈕 ---
if st.sidebar.button("🚀 開始全自動掃描"):
    all_results = []
    
    if target_group == "全部電子股 (Top 150)":
        dl = DataLoader()
        df_info = dl.taiwan_stock_info()
        elec_df = df_info[df_info['industry_category'].str.contains('電子|半導體|光電', na=False)]
        target_dict = {f"{row['stock_id']}.TW": row['stock_name'] for _, row in elec_df.head(150).iterrows()}
    else:
        target_dict = groups[target_group]
    
    st.info(f"📡 正在偵測：距離支撐 {dist_threshold}% 內且風報比 > {min_rr_ratio} 的標的...")
    progress_bar = st.progress(0)
    
    for i, (symbol, name) in enumerate(target_dict.items()):
        try:
            df = yf.Ticker(symbol).history(period="6mo")
            if df.empty:
                df = yf.Ticker(symbol.replace(".TW", ".TWO")).history(period="6mo")
            
            if len(df) < 60: continue
            
            p = df['Close'].iloc[-1].item()
            m10 = df['Close'].rolling(10).mean().iloc[-1].item()
            m20 = df['Close'].rolling(20).mean().iloc[-1].item()
            high_6mo = df['High'].max().item()

            # 核心邏輯：判斷是否靠近支撐 (10日或20日)
            dist_10 = (p - m10) / m10 * 100
            dist_20 = (p - m20) / m20 * 100
            min_dist = min(abs(dist_10), abs(dist_20))
            
            # 判斷是否在支撐上方且距離符合
            if (p >= m10 or p >= m20) and min_dist <= dist_threshold:
                # 計算風報比
                reward = high_6mo - p
                risk = p - (m20 * 0.98) # 停損設在月線下2%
                ratio = round(reward / risk, 2) if risk > 0 else 0
                
                if ratio >= min_rr_ratio:
                    all_results.append({
                        "名稱": name, "代碼": symbol, "目前價格": round(p, 2),
                        "距離支撐%": f"{round(min_dist, 2)}%",
                        "預期獲利%": f"{((reward/p)*100):.1f}%",
                        "風報比": ratio, "狀態": "🎣 進入釣魚區"
                    })
            time.sleep(0.05)
        except: continue
        progress_bar.progress((i + 1) / len(target_dict))

    if all_results:
        st.subheader(f"🏆 終極掃描結果 (門檻: {dist_threshold}%, 風報比: {min_rr_ratio})")
        st.dataframe(pd.DataFrame(all_results).sort_values(by="風報比", ascending=False), use_container_width=True)
    else:
        st.warning("❌ 目前沒有標的同時符合這兩項嚴格條件。")
