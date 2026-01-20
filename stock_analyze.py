import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- 網頁配置 ---
st.set_page_config(page_title="產業權值百科 v13", layout="wide")

# --- 1. 股票靜態字典 (全產業清單) ---
STOCK_DICT = {
    "2330.TW": "台積電", "2454.TW": "聯發科", "2303.TW": "聯電", "3711.TW": "日月光投控", 
    "2379.TW": "瑞昱", "3034.TW": "聯詠", "2337.TW": "旺宏", "2408.TW": "南亞科", 
    "6770.TW": "力積電", "3532.TW": "台勝科", "2317.TW": "鴻海", "2308.TW": "台達電", 
    "2382.TW": "廣達", "2357.TW": "華碩", "2324.TW": "仁寶", "3231.TW": "緯創", 
    "2356.TW": "英業達", "4938.TW": "和碩", "2395.TW": "研華", "3008.TW": "大立光",
    "2881.TW": "富邦金", "2882.TW": "國泰金", "2886.TW": "兆豐金", "2891.TW": "中信金", 
    "2884.TW": "玉山金", "5880.TW": "合庫金", "2880.TW": "華南金", "2885.TW": "元大金", 
    "2892.TW": "第一金", "2883.TW": "開發金", "2603.TW": "長榮", "2609.TW": "陽明", 
    "2615.TW": "萬海", "2618.TW": "長榮航", "2610.TW": "華航", "2605.TW": "新興", 
    "5608.TW": "四維航", "1301.TW": "台塑", "1303.TW": "南亞", "1326.TW": "台化", 
    "6505.TW": "台塑化", "1304.TW": "台聚", "2002.TW": "中鋼", "2014.TW": "中鴻", 
    "1101.TW": "台泥", "1102.TW": "亞泥", "1216.TW": "統一", "2912.TW": "統一超", 
    "2207.TW": "和泰車", "1760.TW": "寶齡富錦", "4147.TW": "龍燈-KY", "6472.TW": "保瑞", 
    "1795.TW": "美時", "2412.TW": "中華電", "3045.TW": "台灣大", "4904.TW": "遠傳",
    "0050.TW": "元大台灣50", "006208.TW": "富邦台50", "0056.TW": "元大高股息", 
    "00878.TW": "國泰永續高股息", "00919.TW": "群益台灣精選高息", "00713.TW": "元大台灣高息低波", 
    "00929.TW": "復華台灣科技優息", "00940.TW": "元大台灣價值高息", "00632R.TW": "元大台灣50反1", 
    "00631L.TW": "元大台灣50正2", "AAPL": "蘋果", "NVDA": "輝達", "TSLA": "特斯拉", 
    "AMD": "超微", "MSFT": "微軟", "GOOGL": "谷歌", "META": "臉書", "AMZN": "亞馬遜"
}

# --- 2. 導航與搜尋功能 ---
st.title("🏆 AI 全產業選股助手 v13.0")

# 搜尋組件：整合名稱與即時股價
with st.expander("🔍 股票即時百科 (輸入代碼查詢名稱與現價)", expanded=True):
    search_input = st.text_input("請輸入代碼 (如: 2330 或 NVDA):").upper().strip()
    if search_input:
        # 處理台灣代碼格式
        target_ticker = f"{search_input}.TW" if search_input.isdigit() else search_input
        stock_name = STOCK_DICT.get(target_ticker, STOCK_DICT.get(search_input, "未知標的"))
        
        if stock_name != "未知標的":
            try:
                # 僅抓取一日數據做即時報價
                quick_data = yf.download(target_ticker if target_ticker in STOCK_DICT else search_input, 
                                         period="2d", interval="1d", progress=False)
                if not quick_data.empty:
                    now_p = round(float(quick_data['Close'].iloc[-1]), 2)
                    pre_p = float(quick_data['Close'].iloc[-2])
                    diff = round(now_p - pre_p, 2)
                    pct = round((diff / pre_p) * 100, 2)
                    color = "red" if diff > 0 else "green"
                    
                    st.markdown(f"### {stock_name} ({search_input})")
                    st.markdown(f"**最新價格：** `{now_p}`  ( <span style='color:{color}'>{diff} / {pct}%</span> )", unsafe_allow_html=True)
                else:
                    st.info(f"該股票名稱為：**{stock_name}** (暫無即時行情數據)")
            except:
                st.info(f"該股票名稱為：**{stock_name}**")
        else:
            st.warning("查無此代碼，請確認是否輸入正確。")

# --- 3. 側邊欄設定 ---
st.sidebar.title("🛠️ 選股策略設定")
market_choice = st.sidebar.selectbox("掃描市場", ["TW", "BOTH", "US"])
total_budget = st.sidebar.number_input("總投資預算", value=1000000)
auto_threshold = st.sidebar.slider("推薦門檻 (分)", 10, 100, 30)

with st.sidebar.expander("⚖️ 權重分配"):
    w_rsi = st.slider("RSI 超賣", 0, 100, 40)
    w_ma = st.slider("MA 金叉", 0, 100, 30)
    w_vol = st.slider("劇烈波動", 0, 100, 20)
    w_vxx = st.slider("成交爆量", 0, 100, 10)

# --- 4. 核心分析邏輯 ---
def analyze_stock(ticker, weights):
    try:
        df = yf.download(ticker, period="100d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 25: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA10'] = ta.sma(df['Close'], length=10)

        curr, prev = df.iloc[-1], df.iloc[-2]
        c_price = float(curr['Close'])
        p_price = float(prev['Close'])
        
        score = 0
        reasons = []
        if float(curr['RSI']) < 25: score += weights['rsi']; reasons.append("RSI超賣")
        if float(prev['MA5']) < float(prev['MA10']) and float(curr['MA5']) > float(curr['MA10']):
            score += weights['ma']; reasons.append("MA金叉")
        
        chg = ((c_price - p_price) / p_price) * 100
        if abs(chg) >= (9.0 if ".TW" in ticker else 7.0):
            score += weights['vol']; reasons.append(f"波動({round(chg,1)}%)")
        if float(curr['Volume']) > df['Volume'].mean() * 2:
            score += weights['vxx']; reasons.append("爆量")

        if score > 0:
            return {
                "名稱": STOCK_DICT.get(ticker, ticker),
                "代碼": ticker, "總分": score, "現價": round(c_price, 2),
                "漲跌": f"{round(chg, 2)}%", "訊號": " + ".join(reasons), "raw_score": score
            }
    except: return None

# --- 5. 執行掃描 ---
if st.button("🚀 執行全自動產業掃描"):
    target_list = list(STOCK_DICT.keys())
    if market_choice == "TW": target_list = [t for t in target_list if ".TW" in t]
    elif market_choice == "US": target_list = [t for t in target_list if ".TW" not in t]
    
    results = []
    progress_bar = st.progress(0)
    
    for idx, t in enumerate(target_list):
        res = analyze_stock(t, {'rsi': w_rsi, 'ma': w_ma, 'vol': w_vol, 'vxx': w_vxx})
        if res: results.append(res)
        progress_bar.progress((idx + 1) / len(target_list))

    if results:
        df_res = pd.DataFrame(results).sort_values("raw_score", ascending=False)
        final = df_res[df_res['raw_score'] >= auto_threshold]
        if not final.empty:
            alloc = total_budget / len(final)
            final['建議量'] = final.apply(lambda x: f"{int(alloc/x['現價']//1000)} 張" if ".TW" in x['代碼'] else f"{int(alloc/x['現價'])} 股", axis=1)
            st.success(f"掃描完畢！符合條件標的如下：")
            st.dataframe(final.drop(columns=['raw_score']), use_container_width=True)
        else:
            st.info(f"無達標標的。最高分為 {df_res.iloc[0]['raw_score']} ({df_res.iloc[0]['名稱']})")
