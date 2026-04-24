import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import time

# 網頁基本設定
st.set_page_config(page_title="韭菜選股 V1", layout="wide")
st.title("🧬 韭菜選股 V1：全自動電子產業掃描儀")

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

# 初始化 Session State 用於存放結果
if 'result_df' not in st.session_state:
    st.session_state.result_df = None

# --- 執行按鈕 ---
if st.sidebar.button("🚀 啟動全自動掃描"):
    all_results = []
    
    # 如果選「全部電子股」，利用 FinMind 抓取
    if target_group == "全部電子股 (Top 150)":
        st.info("正在從 FinMind 撈取全台股電子清單...")
        dl = DataLoader()
        df_info = dl.taiwan_stock_info()
        elec_df = df_info[df_info['industry_category'].str.contains('電子|半導體|光電', na=False)]
        target_dict = {f"{row['stock_id']}.TW": row['stock_name'] for _, row in elec_df.head(150).iterrows()}
    else:
        target_dict = groups[target_group]
    
    st.info(f"正在分析【{target_group}】中，請稍候...")
    progress_bar = st.progress(0)
    
    for i, (symbol, name) in enumerate(target_dict.items()):
        try:
            # 嘗試 .TW 或 .TWO
            tk = yf.Ticker(symbol)
            df = tk.history(period="3mo")
            if df.empty:
                symbol = symbol.replace(".TW", ".TWO")
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
            else:
                if p > m5 and m5 > m20: score += 40; tags.append("趨勢轉正")
                if v_today > v_avg: score += 30; tags.append("量能升溫")
                dist_high = (df['High'].max() - p) / df['High'].max()
                if 0.1 < dist_high < 0.35: score += 30; tags.append("🐟低檔區")

            if score >= threshold:
                all_results.append({"名稱": name, "代碼": symbol, "價格": round(p, 2), "漲跌%": f"{change:.2f}%", "得分": score, "診斷": " | ".join(tags)})
            time.sleep(0.05)
        except: continue
        progress_bar.progress((i + 1) / len(target_dict))

    if all_results:
        st.session_state.result_df = pd.DataFrame(all_results).sort_values(by="得分", ascending=False)
    else:
        st.session_state.result_df = None
        st.warning("無符合門檻標的")

# --- 顯示結果與 AI 報告按鈕 ---
if st.session_state.result_df is not None:
    st.subheader(f"🏆 {target_group} 排行榜")
    st.table(st.session_state.result_df)
    
    # AI 報告生成器
    st.divider()
    st.subheader("🤖 AI 盤後分析助手")
    if st.button("生成 Claude 3 分析指令"):
        top_3 = st.session_state.result_df.head(3).to_string(index=False)
        ai_prompt = f"""
請扮演專業的台股分析師，針對以下「韭菜選股 V1」掃描出的強勢股數據進行盤後解析：

數據如下：
{top_3}

請完成：
1. 針對這三檔標的，簡述目前資金追逐的題材（例如 CPO 或 AI 伺服器）。
2. 為這三檔標的設定明天的「關鍵支撐位」與「目標滿足位」。
3. 根據目前得分，給予「買進、觀望、或減碼」的具體建議。
語氣請保持專業、堅定，並符合台灣投資市場用語。
"""
        st.code(ai_prompt, language="text")
        st.info("☝️ 請複製上方文字，貼給 Claude 3 或 ChatGPT 即可獲得專業分析！")
