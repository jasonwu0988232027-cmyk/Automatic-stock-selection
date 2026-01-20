import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- Streamlit 網頁標題 ---
st.set_page_config(page_title="AI 投資助手", layout="wide")
st.title("🤖 AI 智能選股偵測器")

# --- 側邊欄設定 ---
st.sidebar.header("核心設定")
market_type = st.sidebar.selectbox("選擇市場", ["BOTH", "TW", "US"])
top_n_input = st.sidebar.text_input("推薦數量 (輸入數字或保留空白以自動)", "")
total_budget = st.sidebar.number_input("投資預算", value=1000000)
auto_threshold = st.sidebar.slider("自動模式評分門檻", 0, 100, 50)

# 處理 TOP_N 邏輯
top_n = int(top_n_input) if top_n_input.isdigit() else None

# --- 股票清單 ---
US_STOCKS = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "GOOGL", "META", "AMZN"]
TW_STOCKS = ["2330.TW", "2454.TW", "2317.TW", "2603.TW", "2308.TW", "2382.TW", "2881.TW"]

def scan_market():
    if market_type == "TW": tickers = TW_STOCKS
    elif market_type == "US": tickers = US_STOCKS
    else: tickers = TW_STOCKS + US_STOCKS
    
    results = []
    progress_bar = st.progress(0) # Streamlit 進度條
    status_text = st.empty()
    
    for idx, ticker in enumerate(tickers):
        try:
            status_text.text(f"正在分析: {ticker}...")
            # 更新進度條
            progress_bar.progress((idx + 1) / len(tickers))
            
            time.sleep(0.5) # Streamlit 環境下建議縮短延遲或使用快取
            df = yf.download(ticker, period="100d", interval="1d", progress=False, auto_adjust=True)
            
            if df.empty or len(df) < 30: continue
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)

            # 指標計算
            df['RSI'] = ta.rsi(df['Close'], length=14)
            df['MA5'] = ta.sma(df['Close'], length=5)
            df['MA10'] = ta.sma(df['Close'], length=10)
            
            curr_price = float(df['Close'].iloc[-1])
            prev_price = float(df['Close'].iloc[-2])
            last_rsi = float(df['RSI'].iloc[-1])
            last_ma5 = float(df['MA5'].iloc[-1])
            last_ma10 = float(df['MA10'].iloc[-1])
            prev_ma5 = float(df['MA5'].iloc[-2])
            prev_ma10 = float(df['MA10'].iloc[-2])
            volume = float(df['Volume'].iloc[-1])
            avg_vol = df['Volume'].mean()
            
            score = 0
            triggers = []

            if last_rsi < 20:
                score += 40
                triggers.append("RSI超賣")
            if prev_ma5 < prev_ma10 and last_ma5 > last_ma10:
                score += 30
                triggers.append("MA金叉")
            
            change_pct = ((curr_price - prev_price) / prev_price) * 100
            threshold = 9.5 if ".TW" in ticker else 7.0
            if abs(change_pct) >= threshold:
                score += 20
                triggers.append(f"波動({round(change_pct,1)}%)")
            
            if volume > avg_vol * 2:
                score += 10
                triggers.append("爆量")

            if score > 0:
                results.append({
                    "代碼": ticker,
                    "評分": score,
                    "現價": round(curr_price, 2),
                    "訊號": " + ".join(triggers),
                    "raw_score": score # 用於排序
                })
                
        except Exception as e:
            continue

    status_text.text("分析完成！")
    return results

# --- 啟動按鈕 ---
if st.button("開始 AI 掃描"):
    data = scan_market()
    
    if data:
        df_res = pd.DataFrame(data)
        df_res = df_res.sort_values(by="raw_score", ascending=False)
        
        # 數量篩選
        if top_n is not None:
            final_df = df_res.head(top_n)
        else:
            final_df = df_res[df_res['評分'] >= auto_threshold]
            if final_df.empty: final_df = df_res.head(1)
            
        # 計算建議張數/股數
        allocation = total_budget / len(final_df)
        final_df['建議買進數量'] = final_df.apply(
            lambda x: f"{int(allocation/x['現價']//1000)} 張" if ".TW" in x['代碼'] else f"{int(allocation/x['現價'])} 股", 
            axis=1
        )
        
        st.subheader("🎯 AI 推薦清單")
        st.table(final_df.drop(columns=['raw_score'])) # 顯示漂亮表格
    else:
        st.warning("今日市場未發現符合條件之標的。")
