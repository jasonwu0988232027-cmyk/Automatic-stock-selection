import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- 網頁配置 ---
st.set_page_config(page_title="AI 自定義選股偵測器", layout="wide")

# --- 1. 擴充版股票數據庫 (70+ 檔) ---
TW_STOCKS = [
    "2330.TW", "2454.TW", "2303.TW", "3711.TW", "2379.TW", "3034.TW", "2337.TW", "2408.TW", "6770.TW", "3532.TW",
    "2317.TW", "2308.TW", "2382.TW", "2357.TW", "2324.TW", "3231.TW", "2356.TW", "4938.TW", "2395.TW", "3008.TW",
    "2881.TW", "2882.TW", "2886.TW", "2891.TW", "2884.TW", "5880.TW", "2880.TW", "2885.TW", "2892.TW", "2883.TW",
    "2603.TW", "2609.TW", "2615.TW", "2618.TW", "2610.TW", "2605.TW", "5608.TW",
    "1301.TW", "1303.TW", "1326.TW", "6505.TW", "1304.TW",
    "2002.TW", "2014.TW", "1101.TW", "1102.TW", "2542.TW", "1802.TW", "2501.TW",
    "1216.TW", "2912.TW", "2727.TW", "2707.TW", "9943.TW", "1227.TW", "2207.TW",
    "1760.TW", "4147.TW", "6472.TW", "1752.TW", "1795.TW",
    "2412.TW", "3045.TW", "4904.TW", "8926.TW",
    "0050.TW", "006208.TW", "0056.TW", "00878.TW", "00919.TW", 
    "00713.TW", "00929.TW", "00940.TW", "00632R.TW", "00631L.TW"
]
US_STOCKS = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "GOOGL", "META", "AMZN"]

# --- 2. 側邊欄：權重自定義與基本設定 ---
st.sidebar.title("🛠️ AI 策略控制台")

with st.sidebar.expander("📊 權重占比設定", expanded=True):
    w_rsi = st.slider("RSI 超賣權重", 0, 100, 40)
    w_ma = st.slider("MA 金叉權重", 0, 100, 30)
    w_volatility = st.slider("劇烈波動權重", 0, 100, 20)
    w_volume = st.slider("成交爆量權重", 0, 100, 10)
    total_w = w_rsi + w_ma + w_volatility + w_volume
    st.caption(f"目前總權重分值：{total_w} 分")

market_choice = st.sidebar.selectbox("掃描市場", ["TW", "BOTH", "US"])
top_n_input = st.sidebar.text_input("推薦數量 (留空則依門檻自動)", "")
total_budget = st.sidebar.number_input("總投資預算", value=1000000)
auto_threshold = st.sidebar.slider("自動模式門檻 (分)", 10, total_w, int(total_w*0.5))

# --- 3. 核心分析引擎 ---
@st.cache_data(ttl=3600)
def analyze_stock(ticker, weights):
    try:
        df = yf.download(ticker, period="100d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 30: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA10'] = ta.sma(df['Close'], length=10)

        last = df.iloc[-1]
        prev = df.iloc[-2]
        curr_p = float(last['Close'])
        change_pct = ((curr_p - float(prev['Close'])) / float(prev['Close'])) * 100

        score = 0
        reasons = []

        # 應用自定義權重
        if float(last['RSI']) < 20:
            score += weights['rsi']
            reasons.append(f"RSI超賣(+{weights['rsi']})")
        
        if float(prev['MA5']) < float(prev['MA10']) and float(last['MA5']) > float(last['MA10']):
            score += weights['ma']
            reasons.append(f"MA金叉(+{weights['ma']})")
        
        limit = 9.5 if ".TW" in ticker else 7.0
        if abs(change_pct) >= limit:
            score += weights['volatility']
            reasons.append(f"劇烈波動(+{weights['volatility']})")
            
        if float(last['Volume']) > df['Volume'].mean() * 2:
            score += weights['volume']
            reasons.append(f"成交爆量(+{weights['volume']})")

        if score > 0:
            return {"代碼": ticker, "總分": score, "現價": round(curr_p, 2), 
                    "漲跌幅": f"{round(change_pct, 2)}%", "觸發訊號": " + ".join(reasons)}
    except: return None

# --- 4. 主程式執行 ---
st.title("🏆 AI 全產業自定義權重選股助手")

if st.button("🚀 開始執行個性化掃描"):
    target_list = TW_STOCKS if market_choice == "TW" else (US_STOCKS if market_choice == "US" else TW_STOCKS + US_STOCKS)
    current_weights = {'rsi': w_rsi, 'ma': w_ma, 'volatility': w_volatility, 'volume': w_volume}
    
    results = []
    bar = st.progress(0)
    status = st.empty()

    for i, t in enumerate(target_list):
        status.text(f"🔍 掃描中: {t} ({i+1}/{len(target_list)})")
        res = analyze_stock(t, current_weights)
        if res: results.append(res)
        bar.progress((i + 1) / len(target_list))

    status.success("✅ 掃描完成！")

    if results:
        df_res = pd.DataFrame(results).sort_values("總分", ascending=False)
        top_n = int(top_n_input) if top_n_input.isdigit() else None
        final_df = df_res.head(top_n) if top_n else df_res[df_res['總分'] >= auto_threshold]
        
        if not final_df.empty:
            alloc = total_budget / len(final_df)
            final_df['建議量'] = final_df.apply(lambda x: f"{int(alloc/x['現價']//1000)} 張" if ".TW" in x['代碼'] else f"{int(alloc/x['現價'])} 股", axis=1)
            
            if "00632R.TW" in final_df['代碼'].values:
                st.error("🚨 警告：避險標的「反向50」分數達標，市場風險正在上升！")
            
            st.subheader("📍 AI 選股推薦名單")
            st.dataframe(final_df, use_container_width=True)
        else:
            st.warning(f"沒有股票達到您的門檻分數 ({auto_threshold} 分)。")
    else:
        st.warning("市場中無符合任何訊號的標的。")
