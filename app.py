import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import time

# 網頁基本設定
st.set_page_config(page_title="韭菜選股 V1", layout="wide")
st.title("🧬 韭菜選股 V1：專業交易員版 (含風報比)")

# --- 側邊欄控制區 ---
st.sidebar.header("🔍 釣魚設定")
target_group = st.sidebar.selectbox("1. 選擇魚池 (族群)", 
    ["全部電子股 (Top 150)", "AI 伺服器/代工", "CPO 矽光子", "低軌衛星概念", "載板三雄"])

mode = st.sidebar.selectbox("2. 選股模式", ["釣魚穩健型", "搶短爆發型"])
threshold = st.sidebar.slider("3. 最低門檻分數", 0, 100, 60)

# 定義固定族群
groups = {
    "AI 伺服器/代工": {"2330.TW": "台積電", "2317.TW": "鴻海", "2382.TW": "廣達", "3231.TW": "緯創", "6669.TW": "緯穎", "3017.TW": "奇鋐"},
    "CPO 矽光子": {"3665.TW": "貿聯-KY", "6442.TW": "光聖", "3081.TW": "聯亞", "3363.TWO": "上詮", "3163.TWO": "波若威", "4979.TWO": "華星光"},
    "低軌衛星概念": {"2313.TW": "華通", "2314.TW": "台揚", "3491.TWO": "昇達科", "6274.TWO": "台燿", "2383.TW": "台光電"},
    "載板三雄": {"3037.TW": "欣興", "8046.TW": "南電", "3189.TW": "景碩", "2368.TW": "金像電"}
}

# 初始化 Session State
if 'result_df' not in st.session_state:
    st.session_state.result_df = None

# --- 執行按鈕 ---
if st.sidebar.button("🚀 啟動全自動掃描"):
    all_results = []
    
    if target_group == "全部電子股 (Top 150)":
        st.info("正在從 FinMind 撈取清單...")
        dl = DataLoader()
        df_info = dl.taiwan_stock_info()
        elec_df = df_info[df_info['industry_category'].str.contains('電子|半導體|光電', na=False)]
        target_dict = {f"{row['stock_id']}.TW": row['stock_name'] for _, row in elec_df.head(150).iterrows()}
    else:
        target_dict = groups[target_group]
    
    st.info(f"正在分析【{target_group}】並計算風報比...")
    progress_bar = st.progress(0)
    
    for i, (symbol, name) in enumerate(target_dict.items()):
        try:
            tk = yf.Ticker(symbol)
            df = tk.history(period="6mo") # 抓6個月數據算高點
            if df.empty:
                symbol = symbol.replace(".TW", ".TWO")
                df = yf.Ticker(symbol).history(period="6mo")
            
            if df.empty or len(df) < 22: continue
            
            p = df['Close'].iloc[-1]
            m5 = df['Close'].rolling(5).mean().iloc[-1]
            m20 = df['Close'].rolling(20).mean().iloc[-1]
            v_today = df['Volume'].iloc[-1]
            v_avg = df['Volume'].rolling(5).mean().iloc[-1]
            high_6mo = df['High'].max()
            change = (p - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100

            # 1. 核心評分
            score = 0
            tags = []
            if mode == "搶短爆發型":
                if p > m5: score += 30; tags.append("強勢")
                if change > 2.5: score += 30; tags.append("噴發")
                if v_today > v_avg * 1.5: score += 40; tags.append("🔥爆量")
            else:
                if p > m5 and m5 > m20: score += 40; tags.append("多頭")
                if v_today > v_avg: score += 30; tags.append("量增")
                dist_h = (high_6mo - p) / high_6mo
                if 0.1 < dist_h < 0.35: score += 30; tags.append("🐟釣魚區")

            # 2. 風報比試算 (Reward: 漲回高點空間 / Risk: 跌破月線2%風險)
            reward_space = high_6mo - p
            risk_space = p - (m20 * 0.98)
            rr_ratio = round(reward_space / risk_space, 2) if risk_space > 0 else 0

            if score >= threshold:
                all_results.append({
                    "名稱": name, "代碼": symbol, "價格": round(p, 2),
                    "預期獲利%": f"{((reward_space/p)*100):.1f}%",
                    "風報比": rr_ratio, "得分": score, "診斷": " | ".join(tags)
                })
            time.sleep(0.05)
        except: continue
        progress_bar.progress((i + 1) / len(target_dict))

    st.session_state.result_df = pd.DataFrame(all_results).sort_values(by="風報比", ascending=False) if all_results else None

# --- 顯示結果 ---
if st.session_state.result_df is not None:
    st.subheader(f"🏆 {target_group} 排行榜 (依風報比排序)")
    st.dataframe(st.session_state.result_df, use_container_width=True)
    st.write("💡 **風報比 > 2.0**：代表潛在獲利是風險的兩倍以上，值得進場！")
    
    # AI 報告生成
    if st.button("🤖 生成 AI 盤後分析指令"):
        top_3 = st.session_state.result_df.head(3).to_string(index=False)
        ai_prompt = f"請分析以下數據並給予建議：\n{top_3}\n請特別針對風報比與得分提供明天釣魚的具體點位。"
        st.code(ai_prompt, language="text")
