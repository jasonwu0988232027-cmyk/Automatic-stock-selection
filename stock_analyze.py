import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- 網頁配置 ---
st.set_page_config(page_title="AI 產業權值選股器", layout="wide")

# --- 1. 滿血版全產業龍頭清單 (約 70+ 檔) ---
FULL_TW_LIST = [
    # 半導體/電子代工
    "2330.TW", "2454.TW", "2303.TW", "3711.TW", "2379.TW", "3034.TW", "2337.TW", "2408.TW", "6770.TW", "3532.TW",
    "2317.TW", "2308.TW", "2382.TW", "2357.TW", "2324.TW", "3231.TW", "2356.TW", "4938.TW", "2395.TW", "3008.TW",
    # 金融/航運/傳產
    "2881.TW", "2882.TW", "2886.TW", "2891.TW", "2884.TW", "5880.TW", "2880.TW", "2885.TW", "2892.TW", "2883.TW",
    "2603.TW", "2609.TW", "2615.TW", "2618.TW", "2610.TW", "1301.TW", "1303.TW", "1326.TW", "6505.TW", "2002.TW",
    "1101.TW", "1102.TW", "1216.TW", "2912.TW", "2412.TW", "3045.TW",
    # 生技/熱門/ETF
    "1760.TW", "4147.TW", "6472.TW", "1795.TW", "0050.TW", "006208.TW", "0056.TW", "00878.TW", "00919.TW", 
    "00713.TW", "00929.TW", "00940.TW", "00632R.TW", "00631L.TW"
]
US_LIST = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "GOOGL", "META", "AMZN"]

# --- 2. 側邊欄策略中心 ---
st.sidebar.title("🛠️ 投資決策參數")
market = st.sidebar.selectbox("掃描市場", ["TW", "BOTH", "US"])
total_budget = st.sidebar.number_input("總預算 (TWD/USD)", value=1000000)
auto_threshold = st.sidebar.slider("推薦門檻 (分)", 10, 100, 30)

with st.sidebar.expander("⚖️ 權重占比自定義", expanded=True):
    w_rsi = st.slider("RSI 超賣權重", 0, 100, 40)
    w_ma = st.slider("MA 金叉權重", 0, 100, 30)
    w_vol = st.slider("劇烈波動權重", 0, 100, 20)
    w_vxx = st.slider("成交爆量權重", 0, 100, 10)

# --- 3. 核心運算引擎 (加固邏輯) ---
def analyze_stock(ticker, weights):
    try:
        # 下載數據
        df = yf.download(ticker, period="100d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 25: return None
        
        # 修正欄位結構 (防範 Series 模糊錯誤)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        # 指標計算
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA10'] = ta.sma(df['Close'], length=10)

        # 準確提取標量值
        curr = df.iloc[-1]
        prev = df.iloc[-2]
        c_price = float(curr['Close'])
        p_price = float(prev['Close'])
        c_rsi = float(curr['RSI'])
        
        score = 0
        reasons = []

        # RSI 策略 (加強過濾)
        if c_rsi < 25:
            score += weights['rsi']; reasons.append("RSI超賣")
        # MA 金叉策略
        if float(prev['MA5']) < float(prev['MA10']) and float(curr['MA5']) > float(curr['MA10']):
            score += weights['ma']; reasons.append("MA金叉")
        # 波動策略
        chg = ((c_price - p_price) / p_price) * 100
        limit = 9.0 if ".TW" in ticker else 7.0
        if abs(chg) >= limit:
            score += weights['vol']; reasons.append(f"波動({round(chg,1)}%)")
        # 爆量策略
        if float(curr['Volume']) > df['Volume'].mean() * 2:
            score += weights['vxx']; reasons.append("爆量")

        if score > 0:
            # 獲取中文名稱 (使用 fast_info 減少延遲)
            try:
                name = yf.Ticker(ticker).fast_info.get('common_name', ticker)
            except:
                name = ticker
                
            return {
                "名稱": name,
                "代碼": ticker,
                "總分": score,
                "現價": round(c_price, 2),
                "漲跌": f"{round(chg, 2)}%",
                "訊號": " + ".join(reasons),
                "raw_score": score
            }
    except:
        return None

# --- 4. 網頁顯示邏輯 ---
st.title("🏆 AI 全產業龍頭選股助手 v11.0")

if st.button("🚀 啟動全市場自動化掃描"):
    target = FULL_TW_LIST if market == "TW" else (US_LIST if market == "US" else FULL_TW_LIST + US_LIST)
    weights = {'rsi': w_rsi, 'ma': w_ma, 'vol': w_vol, 'vxx': w_vxx}
    
    results = []
    progress_bar = st.progress(0)
    status_msg = st.empty()

    for idx, t in enumerate(target):
        status_msg.text(f"分析中: {t} ({idx+1}/{len(target)})")
        res = analyze_stock(t, weights)
        if res:
            results.append(res)
        progress_bar.progress((idx + 1) / len(target))
        # 避免觸發 Yahoo API 限制
        if idx % 5 == 0: time.sleep(0.5)

    status_msg.success(f"✅ 掃描完成！共分析 {len(target)} 檔標的。")

    if results:
        res_df = pd.DataFrame(results).sort_values("raw_score", ascending=False)
        final = res_df[res_df['raw_score'] >= auto_threshold]
        
        if not final.empty:
            # 部位配置計算
            alloc = total_budget / len(final)
            final['建議配置'] = final.apply(lambda x: f"{int(alloc/x['現價']//1000)} 張" if ".TW" in x['代碼'] else f"{int(alloc/x['現價'])} 股", axis=1)
            
            # 警示提醒
            if any("00632R" in str(x) for x in final['代碼']):
                st.error("🚨 警告：避險標的「反向50」已達標，請注意大盤回檔風險！")
            
            st.subheader(f"🎯 AI 精選推薦名單 (門檻：{auto_threshold}分)")
            st.dataframe(final.drop(columns=['raw_score']), use_container_width=True)
            st.balloons()
        else:
            st.info(f"今日無標的達標。市場最高分為：{res_df.iloc[0]['raw_score']} 分 (標的: {res_df.iloc[0]['名稱']})")
    else:
        st.warning("市場目前無任何訊號觸發。")
