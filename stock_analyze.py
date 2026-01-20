import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- 配置 ---
st.set_page_config(page_title="AI 選股助手 v10", layout="wide")

# --- 股票池 ---
TW_LIST = [
    "2330.TW", "2454.TW", "2317.TW", "2308.TW", "2382.TW", "2412.TW", "2881.TW", "2882.TW", 
    "2603.TW", "2002.TW", "1101.TW", "0050.TW", "0056.TW", "00878.TW", "00632R.TW"
] # 測試時建議先用精簡版，確認成功後再手動加回前面的長清單

US_LIST = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT"]

# --- 側邊欄 ---
st.sidebar.title("🛠️ 策略參數")
market = st.sidebar.selectbox("市場", ["TW", "US", "BOTH"])
total_budget = st.sidebar.number_input("預算", value=1000000)
auto_threshold = st.sidebar.slider("推薦門檻", 10, 100, 30)

with st.sidebar.expander("📊 權重設定"):
    w_rsi = st.slider("RSI超賣", 0, 100, 40)
    w_ma = st.slider("MA金叉", 0, 100, 30)
    w_vol = st.slider("大波動", 0, 100, 20)
    w_vxx = st.slider("爆量", 0, 100, 10)

# --- 分析函數 ---
def analyze_stock(ticker):
    try:
        # 1. 抓取歷史數據 (100天)
        df = yf.download(ticker, period="100d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 20: return None
        
        # 2. 欄位清洗 (處理 Multi-Index)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 3. 指標計算
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA10'] = ta.sma(df['Close'], length=10)

        # 4. 取最新值 (使用 .iloc[-1] 確保是標量)
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        
        c_price = float(curr['Close'])
        p_price = float(prev['Close'])
        c_rsi = float(curr['RSI'])
        chg = ((c_price - p_price) / p_price) * 100
        
        # 5. 計分
        score = 0
        reasons = []
        if c_rsi < 30: # 稍微放寬門檻
            score += w_rsi; reasons.append("RSI超賣")
        if float(prev['MA5']) < float(prev['MA10']) and float(curr['MA5']) > float(curr['MA10']):
            score += w_ma; reasons.append("MA金叉")
        if abs(chg) > (9.5 if ".TW" in ticker else 7.0):
            score += w_vol; reasons.append(f"波動({round(chg,1)}%)")
        if float(curr['Volume']) > df['Volume'].mean() * 1.5:
            score += w_vxx; reasons.append("爆量")

        if score > 0:
            return {
                "名稱": ticker, # 為了穩定性先用代碼代替名稱抓取
                "總分": score,
                "現價": round(c_price, 2),
                "漲跌": f"{round(chg, 2)}%",
                "訊號": " + ".join(reasons)
            }
    except Exception as e:
        st.write(f"⚠️ {ticker} 數據異常: {e}")
        return None

# --- 主程式 ---
st.title("🤖 AI 選股助手 v10.0")

if st.button("🚀 開始全自動掃描"):
    target = TW_LIST if market == "TW" else (US_LIST if market == "US" else TW_LIST + US_LIST)
    
    results = []
    progress = st.progress(0)
    
    # 使用 st.empty 建立動態日誌區
    log_area = st.empty()

    for idx, t in enumerate(target):
        log_area.text(f"正在掃描 ({idx+1}/{len(target)}): {t}")
        data = analyze_stock(t)
        if data:
            results.append(data)
        progress.progress((idx + 1) / len(target))
        time.sleep(0.2) # 加入微小延遲防止被 Yahoo 封鎖

    log_area.empty()

    if results:
        res_df = pd.DataFrame(results).sort_values("總分", ascending=False)
        final = res_df[res_df['總分'] >= auto_threshold]
        
        if not final.empty:
            st.success(f"找到 {len(final)} 檔符合條件標的！")
            st.dataframe(final, use_container_width=True)
        else:
            st.info(f"掃描完畢，但無股票超過門檻 ({auto_threshold}分)。最高分為: {res_df.iloc[0]['總分']}")
    else:
        st.error("❌ 掃描失敗：未獲取到任何有效數據。請檢查您的網路或 yfinance 是否需要更新。")
