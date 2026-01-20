import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- 網頁配置 ---
st.set_page_config(page_title="AI 產業龍頭偵測器", layout="wide")

# --- 1. 股票數據庫 ---
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

# --- 2. 側邊欄控制 ---
st.sidebar.title("🛠️ 策略微調")

with st.sidebar.expander("📊 權重設定", expanded=True):
    w_rsi = st.slider("RSI 超賣權重", 0, 100, 40)
    w_ma = st.slider("MA 金叉權重", 0, 100, 30)
    w_volatility = st.slider("劇烈波動權重", 0, 100, 20)
    w_volume = st.slider("成交爆量權重", 0, 100, 10)
    total_w = w_rsi + w_ma + w_volatility + w_volume

market_choice = st.sidebar.selectbox("掃描市場", ["TW", "BOTH", "US"])
top_n_input = st.sidebar.text_input("推薦數量 (留空則自動)", "")
total_budget = st.sidebar.number_input("總預算", value=1000000)
auto_threshold = st.sidebar.slider("推薦門檻 (分)", 0, total_w, 30) # 調低預設門檻避免無訊號

# --- 3. 穩定分析引擎 ---
@st.cache_data(ttl=600)
def analyze_stock(ticker, weights):
    try:
        # 下載數據
        df = yf.download(ticker, period="100d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 30: return None
        
        # 修正欄位結構
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 指標計算
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA10'] = ta.sma(df['Close'], length=10)

        # 關鍵加固：確保取出的值是 float 標量
        last_price = float(df['Close'].iloc[-1])
        prev_price = float(df['Close'].iloc[-2])
        last_rsi = float(df['RSI'].iloc[-1])
        last_ma5 = float(df['MA5'].iloc[-1])
        last_ma10 = float(df['MA10'].iloc[-1])
        prev_ma5 = float(df['MA5'].iloc[-2])
        prev_ma10 = float(df['MA10'].iloc[-2])
        last_vol = float(df['Volume'].iloc[-1])
        avg_vol = float(df['Volume'].mean())

        score = 0
        reasons = []

        # RSI 判斷 (解決 Series 模糊問題)
        if last_rsi < 20:
            score += weights['rsi']
            reasons.append("RSI超賣")
        
        # MA 金叉判斷
        if prev_ma5 < prev_ma10 and last_ma5 > last_ma10:
            score += weights['ma']
            reasons.append("MA金叉")
        
        # 漲跌幅判斷
        change_pct = ((last_price - prev_price) / prev_price) * 100
        limit = 9.5 if ".TW" in ticker else 7.0
        if abs(change_pct) >= limit:
            score += weights['volatility']
            reasons.append(f"大波動({round(change_pct,1)}%)")
            
        # 爆量判斷
        if last_vol > avg_vol * 2:
            score += weights['volume']
            reasons.append("爆量")

        # 獲取名稱
        name = yf.Ticker(ticker).info.get('shortName', ticker)

        if score > 0:
            return {
                "股票名稱": name,
                "代碼": ticker,
                "總分": score,
                "現價": round(last_price, 2),
                "漲跌": f"{round(change_pct,2)}%",
                "訊號": " + ".join(reasons),
                "raw_score": score
            }
    except:
        return None

# --- 4. 執行與顯示 ---
st.title("🏆 AI 產業龍頭選股助手 v9.0")

if st.button("🚀 開始穩定掃描"):
    target = TW_STOCKS if market_choice == "TW" else (US_STOCKS if market_choice == "US" else TW_STOCKS + US_STOCKS)
    weights = {'rsi': w_rsi, 'ma': w_ma, 'volatility': w_volatility, 'volume': w_volume}
    
    results = []
    bar = st.progress(0)
    
    for i, t in enumerate(target):
        res = analyze_stock(t, weights)
        if res: results.append(res)
        bar.progress((i + 1) / len(target))

    if results:
        df = pd.DataFrame(results).sort_values("raw_score", ascending=False)
        top_n = int(top_n_input) if top_n_input.isdigit() else None
        final = df.head(top_n) if top_n else df[df['raw_score'] >= auto_threshold]
        
        if not final.empty:
            st.success(f"掃描完畢！符合門檻的股票共 {len(final)} 檔。")
            st.dataframe(final.drop(columns=['raw_score']), use_container_width=True)
        else:
            st.warning(f"掃描完成，但最高分為 {df.iloc[0]['raw_score']}，未達門檻 {auto_threshold}。請嘗試調低側邊欄門檻。")
    else:
        st.error("掃描異常，請確認網路連接或 Ticker 清單正確性。")
