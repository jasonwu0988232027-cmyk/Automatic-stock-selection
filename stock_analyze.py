import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time

# --- 網頁配置 ---
st.set_page_config(page_title="產業權值百科 v13", layout="wide")

# --- 1. 股票靜態字典 (全產業清單) ---
STOCK_DICT = {
    # 水泥工業
    "1101.TW": "台泥", "1102.TW": "亞泥", "1108.TW": "幸福", "1109.TW": "信大", "1110.TW": "東泥",
    # 食品工業
    "1216.TW": "統一", "1210.TW": "大成", "1215.TW": "卜蜂", "1227.TW": "佳格", "1229.TW": "聯華", "1231.TW": "聯華食",
    # 塑膠工業
    "1301.TW": "台塑", "1303.TW": "南亞", "1326.TW": "台化", "1304.TW": "台聚", "1308.TW": "亞聚", "1309.TW": "台達化",
    # 紡織纖維
    "1402.TW": "遠東新", "1476.TW": "儒鴻", "1477.TW": "聚陽", "1409.TW": "新纖", "1444.TW": "力麗",
    # 電器機械
    "1503.TW": "士電", "1504.TW": "東元", "1513.TW": "中興電", "1519.TW": "華城", "1560.TW": "中砂", "1590.TW": "亞德客-KY",
    # 電器電纜
    "1605.TW": "華新", "1608.TW": "華榮", "1609.TW": "大亞", "1611.TW": "中電", "1618.TW": "合機",
    # 化學工業
    "1717.TW": "長興", "1722.TW": "台肥", "1723.TW": "中碳", "1712.TW": "興農", "1710.TW": "東聯",
    # 生技醫療
    "6446.TW": "藥華藥", "1795.TW": "美時", "6472.TW": "保瑞", "4147.TW": "龍燈-KY", "1707.TW": "葡萄王", "4743.TW": "合一",
    # 玻璃陶瓷
    "1802.TW": "台玻", "1806.TW": "冠軍", "1809.TW": "中釉",
    # 造紙工業
    "1907.TW": "永豐餘", "1904.TW": "正隆", "1909.TW": "榮成", "1905.TW": "華紙",
    # 鋼鐵工業
    "2002.TW": "中鋼", "2014.TW": "中鴻", "2027.TW": "大鴻", "2031.TW": "新光鋼", "9958.TW": "世紀鋼", "2006.TW": "東和鋼鐵",
    # 橡膠工業
    "2105.TW": "正新", "2106.TW": "建大", "2101.TW": "南港", "2103.TW": "台橡",
    # 汽車工業
    "2207.TW": "和泰車", "2201.TW": "裕隆", "2204.TW": "中華", "2206.TW": "三陽工業", "2247.TW": "汎德永業",
    # 半導體業
    "2330.TW": "台積電", "2454.TW": "聯發科", "2303.TW": "聯電", "3711.TW": "日月光投控", "3661.TW": "世芯-KY", "3034.TW": "聯詠", "2379.TW": "瑞昱", "2408.TW": "南亞科", "6415.TW": "矽力*-KY", "2344.TW": "華邦電",
    # 電腦周邊
    "2382.TW": "廣達", "2357.TW": "華碩", "2324.TW": "仁寶", "3231.TW": "緯創", "2376.TW": "技嘉", "2301.TW": "光寶科", "2395.TW": "研華", "4938.TW": "和碩",
    # 光電業
    "3008.TW": "大立光", "2409.TW": "友達", "3481.TW": "群創", "3406.TW": "玉晶光", "2406.TW": "國碩", "6116.TW": "彩晶",
    # 通信網路
    "2412.TW": "中華電", "3045.TW": "台灣大", "4904.TW": "遠傳", "2345.TW": "智邦", "6285.TW": "啟碁", "5388.TW": "中磊",
    # 電子組件
    "2308.TW": "台達電", "2327.TW": "國巨", "3037.TW": "欣興", "2383.TW": "台光電", "3044.TW": "健鼎", "2368.TW": "金像電",
    # 電子通路
    "3702.TW": "大聯大", "3036.TW": "文曄", "2347.TW": "聯強", "8112.TW": "至上", "5434.TW": "崇越",
    # 資訊服務
    "6214.TW": "精誠", "6183.TW": "關貿", "2480.TW": "敦陽科", "5403.TW": "中菲",
    # 其他電子
    "2317.TW": "鴻海", "2474.TW": "可成", "2360.TW": "致茂", "6139.TW": "亞翔", "2404.TW": "漢唐",
    # 建材營造
    "2542.TW": "興富發", "2548.TW": "華固", "5534.TW": "長虹", "5522.TW": "遠雄", "2501.TW": "國建", "2520.TW": "冠德",
    # 航運業
    "2603.TW": "長榮", "2609.TW": "陽明", "2615.TW": "萬海", "2610.TW": "華航", "2618.TW": "長榮航", "2633.TW": "台灣高鐵",
    # 觀光餐旅
    "2707.TW": "晶華", "2727.TW": "王品", "2731.TW": "雄獅", "2748.TW": "雲品", "2704.TW": "國賓",
    # 金融保險
    "2881.TW": "富邦金", "2882.TW": "國泰金", "2891.TW": "中信金", "2886.TW": "兆豐金", "2884.TW": "玉山金", "5880.TW": "合庫金", "2885.TW": "元大金", "2892.TW": "第一金", "2880.TW": "華南金", "2883.TW": "開發金",
    # 貿易百貨
    "2912.TW": "統一超", "8454.TW": "富邦媒", "2903.TW": "遠百", "5904.TW": "寶雅",
    # 郵電燃氣
    "8908.TW": "欣雄", "8931.TW": "欣高", "6505.TW": "台塑化",
    # 綠能環保
    "9930.TW": "中聯資源", "6806.TW": "森崴能源", "6869.TW": "雲豹能源", "3708.TW": "上緯投控",
    # 數位雲端
    "6689.TW": "伊雲谷", "6173.TW": "浪凡", "6906.TW": "現觀科",
    # 運動休閒
    "9904.TW": "寶成", "9910.TW": "豐泰", "9914.TW": "美利達", "9921.TW": "巨大", "1736.TW": "喬山",
    # 居家生活
    "8464.TW": "億豐", "9911.TW": "櫻花", "9934.TW": "成霖",
    # 其他
    "9933.TW": "中鼎", "9907.TW": "統一實", "9938.TW": "百和",
    # ETF / 反向 / 槓桿
    "0050.TW": "元大台灣50", "006208.TW": "富邦台50", "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", 
    "00919.TW": "群益台灣精選高息", "00929.TW": "復華台灣科技優息", "00632R.TW": "元大台灣50反1", "00631L.TW": "元大台灣50正2",
    # 政府公債 ETF
    "00679B.TW": "元大美債20年", "00687B.TW": "國泰美債20年", "00795B.TW": "中信美國公債20年", "00696B.TW": "富邦美債20年",
    # 美股龍頭
    "AAPL": "蘋果", "NVDA": "輝達", "TSLA": "特斯拉", "AMD": "超微", "MSFT": "微軟", "GOOGL": "谷歌", "META": "臉書", "AMZN": "亞馬遜"
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
