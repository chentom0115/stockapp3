import streamlit as st
import yfinance as yf
import pandas as pd
from FinMind.data import DataLoader
import plotly.graph_objects as go
from plotly.subplots import make_subplots

FINMIND_TOKEN = ""

st.set_page_config(page_title="韭菜選股 V2 - 回測版", layout="wide")
st.title("🚀 韭菜選股 V2（含勝率回測）")

# ================= 側邊欄 =================
with st.sidebar:
    st.header("🔍 選股設定")
    模式 = st.radio("模式", ["爆發型", "釣魚型"])

    if 模式 == "爆發型":
        change_threshold = st.slider("漲幅%", 1.0, 7.0, 2.5)
        vol_multiplier = st.slider("量能倍數", 1.0, 3.0, 1.5)
    else:
        dist_threshold = st.slider("距離MA20%", 0.5, 8.0, 4.5)

    scan_btn = st.button("開始掃描")

# ================= 股票池 =================
@st.cache_data(ttl=3600)
def get_pool():
    return {
        "2330.TW": "台積電",
        "2317.TW": "鴻海",
        "6669.TW": "緯穎",
        "2382.TW": "廣達",
        "3231.TW": "緯創"
    }

# ================= 掃描 =================
if scan_btn:
    pool = get_pool()
    results = []

    for sid, name in pool.items():
        df = yf.Ticker(sid).history(period="6mo")
        if df.empty or len(df) < 60:
            continue

        p = df['Close'].iloc[-1]
        ma5 = df['Close'].rolling(5).mean().iloc[-1]
        ma20 = df['Close'].rolling(20).mean().iloc[-1]
        vol = df['Volume'].iloc[-1]
        vol_avg = df['Volume'].rolling(5).mean().iloc[-1]

        change = (df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2] * 100

        score = 0

        if 模式 == "爆發型":
            if p > ma5: score += 30
            if change > change_threshold: score += 30
            if vol > vol_avg * vol_multiplier: score += 40

        else:
            dist = (p - ma20) / ma20 * 100
            if 0 <= dist <= dist_threshold:
                score = 70

        if score >= 60:
            results.append({
                "名稱": name,
                "代碼": sid,
                "價格": round(p, 1),
                "得分": score
            })

    st.session_state.df = pd.DataFrame(results)

# ================= 排行榜 =================
if "df" in st.session_state:
    st.subheader("🏆 排行榜")
    st.dataframe(st.session_state.df)

# ================= 單股 =================
st.subheader("📈 單股分析")

sid = st.text_input("輸入股票", "6669.TW")

if sid:
    df = yf.Ticker(sid).history(period="6mo")

    if not df.empty:

        # ===== 指標 =====
        df['MA5'] = df['Close'].rolling(5).mean()
        df['MA20'] = df['Close'].rolling(20).mean()
        df['MA60'] = df['Close'].rolling(60).mean()
        df['vol_avg'] = df['Volume'].rolling(5).mean()

        # ===== 訊號 =====
        df['signal'] = (
            (df['Close'] > df['MA5']) &
            (df['MA5'] > df['MA20']) &
            (df['Volume'] > df['vol_avg'] * 1.2)
        )

        signal_df = df[df['signal']]

        # ===== 畫圖 =====
        fig = make_subplots(rows=2, cols=1, shared_xaxes=True,
                            row_heights=[0.7, 0.3])

        fig.add_trace(go.Candlestick(
            x=df.index,
            open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'],
            name='K線'
        ), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['MA5'], name='MA5',
                                 line=dict(color='yellow')), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['MA20'], name='MA20',
                                 line=dict(color='blue')), row=1, col=1)

        fig.add_trace(go.Scatter(x=df.index, y=df['MA60'], name='MA60',
                                 line=dict(color='red', dash='dot')), row=1, col=1)

        # ▲訊號
        fig.add_trace(go.Scatter(
            x=signal_df.index,
            y=signal_df['Low'] * 0.98,
            mode='markers',
            marker=dict(symbol='triangle-up', color='lime', size=10),
            name='起漲'
        ), row=1, col=1)

        # 成交量
        fig.add_trace(go.Bar(
            x=df.index,
            y=df['Volume'],
            name='Volume'
        ), row=2, col=1)

        fig.update_layout(template='plotly_dark', height=600)
        st.plotly_chart(fig, use_container_width=True)

        # ================= 回測 =================
        st.subheader("📊 ▲回測")

        take_profit = 0.08
        stop_loss = 0.04
        hold_days = 10

        results = []

        for idx in signal_df.index:
            entry = df.loc[idx, 'Close']
            entry_i = df.index.get_loc(idx)

            exit_price = entry
            ret = 0
            reason = "時間到"

            for i in range(entry_i+1, min(entry_i+1+hold_days, len(df))):
                price = df['Close'].iloc[i]
                change = (price - entry) / entry

                if change >= take_profit:
                    exit_price = price
                    ret = change
                    reason = "停利"
                    break

                if change <= -stop_loss:
                    exit_price = price
                    ret = change
                    reason = "停損"
                    break

                if i == entry_i+hold_days-1:
                    exit_price = price
                    ret = change

            results.append({
                "日期": idx.strftime("%Y-%m-%d"),
                "報酬%": round(ret*100,2),
                "結果": "✅" if ret>0 else "❌",
                "原因": reason
            })

        bt = pd.DataFrame(results)

        if not bt.empty:
            win = (bt["結果"]=="✅").mean()*100
            avg = bt["報酬%"].mean()

            col1, col2 = st.columns(2)
            col1.metric("勝率", f"{win:.1f}%")
            col2.metric("平均報酬", f"{avg:.2f}%")

            st.dataframe(bt)

        else:
            st.warning("沒有訊號")
