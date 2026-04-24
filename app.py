import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import time

# 網頁基本設定
st.set_page_config(page_title="韭菜選股 AI App", layout="wide")
st.title("🎣 韭菜選股 V1：產業全自動掃描儀")

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 選股設定")
target_group = st.sidebar.selectbox("1. 選擇魚池 (族群)", 
    ["AI 伺服器/代工", "CPO 矽光子", "低軌衛星概念", "載板三雄"])

mode = st.sidebar.selectbox("2. 選股模式", ["釣魚穩健型", "搶短爆發型"])
threshold = st.sidebar.slider("3. 最低門檻分數", 0, 100, 60)

# 定義族群資料
groups = {
    "AI 伺服器/代工": {"2330.TW": "台積電", "2317.TW": "鴻海", "2382.TW": "廣達", "3231.TW": "緯創", "6669.TW": "緯穎", "3017.TW": "奇鋐"},
    "CPO 矽光子": {"3665.TW": "貿聯-KY", "6442.TW": "光聖", "3081.TW": "聯亞", "3363.TWO": "上詮", "3163.TWO": "波若威", "4979.TWO": "華星光"},
    "低軌衛星概念": {"2313.TW": "華通", "2314.TW": "台揚", "3491.TWO": "昇達科", "6274.TWO": "台燿", "2383.TW": "台光電"},
    "載板三雄": {"3037.TW": "欣興", "8046.TW": "南電", "3189.TW": "景碩", "2368.TW": "金像電"}
}

if st.sidebar.button("🚀 啟動全自動掃描"):
    target_list = groups[target_group]
    all_results = []
    
    st.info(f"正在分析【{target_group}】族群，模式：{mode}...")
    progress_bar = st.progress(0)
    
    # 開始掃描
    for i, (symbol, name) in enumerate(target_list.items()):
        try:
            tk = yf.Ticker(symbol)
            df = tk.history(period="3mo")
            if df.empty or len(df) < 20: continue
            
            p = df['Close'].iloc[-1]
            m5 = df['Close'].rolling(5).mean().iloc[-1]
            m20 = df['Close'].rolling(20).mean().iloc[-1]
            v_today = df['Volume'].iloc[-1]
            v_avg = df['Volume'].rolling(5).mean().iloc[-1]
            change = (p - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100

            score = 0
            tags = []

            if mode == "搶短爆發型":
                if p > m5: score += 30; tags.append("強勢慣性")
                if change > 2.5: score += 30; tags.append("動能噴發")
                if v_today > v_avg * 1.5: score += 40; tags.append("🔥主力對敲")
            else: # 釣魚穩健型
                if p > m5 and m5 > m20: score += 40; tags.append("趨勢轉正")
                if v_today > v_avg: score += 30; tags.append("量能升溫")
                dist_high = (df['High'].max() - p) / df['High'].max()
                if 0.1 < dist_high < 0.35: score += 30; tags.append("🐟低檔區")

            if score >= threshold:
                all_results.append({
                    "名稱": name, "代碼": symbol, "價格": round(p, 2),
                    "漲跌%": f"{change:.2f}%", "得分": score, "診斷": " | ".join(tags)
                })
            time.sleep(0.1)
        except: continue
        progress_bar.progress((i + 1) / len(target_list))

    if all_results:
        st.subheader(f"🏆 {target_group} 排行榜")
        res_df = pd.DataFrame(all_results).sort_values(by="得分", ascending=False)
        st.dataframe(res_df, use_container_width=True)
    else:
        st.warning(f"目前【{target_group}】中無標的符合 {threshold} 分門檻。")
