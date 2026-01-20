import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- 網頁配置 ---
st.set_page_config(page_title="AI 全產業龍頭選股器", layout="wide")

# --- 1. 巨量股票數據庫 (涵蓋台股各行業前 10 名龍頭 + ETF) ---
TW_STOCKS = [
    # 半導體/IC設計
    "2330.TW", "2454.TW", "2303.TW", "3711.TW", "2379.TW", "3034.TW", "2337.TW", "2408.TW", "6770.TW", "3532.TW",
    # 電子代工/設備
    "2317.TW", "2308.TW", "2382.TW", "2357.TW", "2324.TW", "3231.TW", "2356.TW", "4938.TW", "2395.TW", "3008.TW",
    # 金融保險
    "2881.TW", "2882.TW", "2886.TW", "2891.TW", "2884.TW", "5880.TW", "2880.TW", "2885.TW", "2892.TW", "2883.TW",
    # 航運/物流
    "2603.TW", "2609.TW", "2615.TW", "2618.TW", "2610.TW", "2605.TW", "5608.TW",
    # 塑化/油氣
    "1301.TW", "1303.TW", "1326.TW", "6505.TW", "1304.TW",
    # 鋼鐵/水泥/建材
    "2002.TW", "2014.TW", "1101.TW", "1102.TW", "2542.TW", "1802.TW", "2501.TW",
    # 食品/觀光/百貨
    "1216.TW", "2912.TW", "2727.TW", "2707.TW", "9943.TW", "1227.TW", "2207.TW",
    # 生技/醫療
    "1760.TW", "4147.TW", "6472.TW", "1752.TW", "1795.TW",
    # 電信/公用事業
    "2412.TW", "3045.TW", "4904.TW", "8926.TW",
    # 指數 ETF 與 避險標的
    "0050.TW", "006208.TW", "0056.TW", "00878.TW", "00919.TW", 
    "00713.TW", "00929.TW", "00940.TW", "00632R.TW", "00631L.TW"
]

US_STOCKS = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "GOOGL", "META", "AMZN"]

# --- 2. 側邊欄控制面板 ---
st.sidebar.title("🛠️ AI 策略設定")
market_choice = st.sidebar.selectbox("1. 掃描市場", ["TW", "BOTH", "US"])
top_n_input = st.sidebar.text_input("2. 推薦名額 (留空則自動篩選)", "")
total_budget = st.sidebar.number_input("3. 投資總預算", value=1000000, step=100000)
auto_threshold = st.sidebar.slider("4. 自動模式門檻 (分)", 30, 100, 50)
stop_loss_pct = st.sidebar.slider("5. 停損基準 (%)", 1, 15, 7) / 100

# --- 3. 核心分析引擎 (含快取機制) ---
@st.cache_data(ttl=3600)
def analyze_stock(ticker):
    try:
        df = yf.download(ticker, period="100d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 30: return None
        
        # 修正新版 yfinance 多重索引問題
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 技術指標計算
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA10'] = ta.sma(df['Close'], length=10)

        last = df.iloc[-1]
        prev = df.iloc[-2]
        curr_p = float(last['Close'])
        prev_p = float(prev['Close'])
        change_pct = ((curr_p - prev_p) / prev_p) * 100

        # --- 評分系統 ---
        score = 0
        reasons = []

        if float(last['RSI']) < 20:
            score += 40
            reasons.append("RSI超賣")
        if float(prev['MA5']) < float(prev['MA10']) and float(last['MA5']) > float(last['MA10']):
            score += 30
            reasons.append("5/10MA金叉")
        
        limit = 9.5 if ".TW" in ticker else 7.0
        if abs(change_pct) >= limit:
            score += 20
            reasons.append(f"波動({round(change_pct,1)}%)")
        if float(last['Volume']) > df['Volume'].mean() * 2:
            score += 10
            reasons.append("成交爆量")

        if score > 0:
            return {
                "代碼": ticker,
                "評分": score,
                "現價": round(curr_p, 2),
                "漲跌幅": f"{round(change_pct, 2)}%",
                "觸發訊號": " + ".join(reasons),
                "raw_score": score
            }
    except Exception:
        return None

# --- 4. 主程式執行介面 ---
st.title("🏆 AI 全產業龍頭選股助手")
st.markdown(f"**監控中：** 台股各產業龍頭及 ETF 共 {len(TW_STOCKS)} 檔，美股科技權值 {len(US_STOCKS)} 檔。")

if st.button("🚀 執行全自動產業掃描"):
    target_list = TW_STOCKS if market_choice == "TW" else (US_STOCKS if market_choice == "US" else TW_STOCKS + US_STOCKS)
    
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()

    for i, ticker in enumerate(target_list):
        status_text.text(f"🔍 正在掃描行業龍頭: {ticker} ({i+1}/{len(target_list)})")
        res = analyze_stock(ticker)
        if res:
            results.append(res)
        progress_bar.progress((i + 1) / len(target_list))

    status_text.success("✅ 全產業掃描完成！")

    if results:
        # 排序與篩選
        df_res = pd.DataFrame(results).sort_values("raw_score", ascending=False)
        top_n = int(top_n_input) if top_n_input.isdigit() else None
        
        if top_n:
            final_df = df_res.head(top_n).copy()
        else:
            final_df = df_res[df_res['raw_score'] >= auto_threshold].copy()
            if final_df.empty: final_df = df_res.head(1).copy()

        # 5. 計算部位配置
        num_picks = len(final_df)
        allocation = total_budget / num_picks
        
        final_df['建議買入數量'] = final_df.apply(
            lambda x: f"{int(allocation/x['現價']//1000)} 張" if ".TW" in x['代碼'] else f"{int(allocation/x['現價'])} 股", 
            axis=1
        )
        final_df['停損參考價'] = (final_df['現價'] * (1 - stop_loss_pct)).round(2)

        # --- 特殊提醒：反向 50 ---
        if "00632R.TW" in final_df['代碼'].values:
            st.error("🚨 **市場警訊**：AI 推薦了『元大台灣50反1』！這代表大盤多數龍頭股技術指標轉弱，請嚴格執行避險或停損。")

        # 顯示結果
        st.subheader(f"🎯 AI 推薦清單 ({'手動' if top_n else '自動'}模式)")
        st.table(final_df.drop(columns=['raw_score']))
        st.balloons()
    else:
        st.warning("今日市場指標未觸發任何推薦訊號。")
