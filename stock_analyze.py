import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
import requests

# ==================== 使用者設定區 ====================
LINE_TOKEN = "你的_LINE_NOTIFY_TOKEN"
MARKET_TYPE = "BOTH"  
TOP_N = None           # [修改點] 設定數字則推薦固定數量；設定 None 則由 AI 自動判定門檻
TOTAL_BUDGET = 1000000 
STOP_LOSS_PCT = 0.07   
AUTO_THRESHOLD = 50    # [新增] 自動模式下，評分超過幾分才推薦 (50分代表至少有強烈超賣或金叉)
# ====================================================

US_STOCKS = ["AAPL", "NVDA", "TSLA", "AMD", "MSFT", "GOOGL", "META", "AMZN"]
TW_STOCKS = ["2330.TW", "2454.TW", "2317.TW", "2603.TW", "2308.TW", "2382.TW", "2881.TW"]

def scan_market():
    tickers = TW_STOCKS if MARKET_TYPE == "TW" else (US_STOCKS if MARKET_TYPE == "US" else TW_STOCKS + US_STOCKS)
    results = []
    
    print(f"🚀 AI 啟動：市場 [{MARKET_TYPE}] | 推薦模式: {'自動' if TOP_N is None else f'精選前 {TOP_N} 名'}")
    
    for ticker in tickers:
        try:
            time.sleep(1)
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
            
            score = 0
            triggers = []

            # 訊號判斷
            if last_rsi < 20:
                score += 40
                triggers.append(f"🔴RSI超賣({round(last_rsi,1)})")
            if prev_ma5 < prev_ma10 and last_ma5 > last_ma10:
                score += 30
                triggers.append("🟡MA金叉")
            
            change_pct = ((curr_price - prev_price) / prev_price) * 100
            threshold = 9.5 if ".TW" in ticker else 7.0
            if abs(change_pct) >= threshold:
                score += 20
                triggers.append(f"🟠大波動({round(change_pct,1)}%)")
            
            # 成交量判定
            volume = float(df['Volume'].iloc[-1])
            avg_vol = df['Volume'].mean()
            if volume > avg_vol * 2:
                score += 10
                triggers.append("🟢爆量")

            # 只要有分數就先記錄
            if score > 0:
                results.append({
                    "ticker": ticker,
                    "score": score,
                    "price": curr_price,
                    "triggers": triggers
                })
                
        except Exception as e:
            print(f"分析 {ticker} 時跳過: {str(e)}")

    # --- 核心邏輯：推薦數量決定 ---
    if results:
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # 決定最終清單
        if TOP_N is not None:
            final_selection = results[:TOP_N]
        else:
            # 自動模式：只挑選超過門檻高分的股票
            final_selection = [r for r in results if r['score'] >= AUTO_THRESHOLD]
            # 如果沒有超過門檻的，就保底給出最高分的一支
            if not final_selection:
                final_selection = [results[0]]

        # 計算報告
        report = f"\n🎯 AI 嚴選推薦名單 ({'自動模式' if TOP_N is None else '手動限額'})："
        
        # 預算分配
        num_picks = len(final_selection)
        allocation = TOTAL_BUDGET / num_picks
        
        for item in final_selection:
            t = item['ticker']
            p = item['price']
            units = int(allocation / p)
            unit_name = "股"
            if ".TW" in t:
                units = units // 1000
                unit_name = "張"
            
            stop_loss = p * (1 - STOP_LOSS_PCT)
            
            report += (f"\n【{t}】評分:{item['score']}\n"
                       f"訊號: {'+'.join(item['triggers'])}\n"
                       f"現價: {round(p,2)} | 建議: {units}{unit_name}\n"
                       f"📍停損參考: {round(stop_loss,2)}")
            
        print(report)
        # send_line_message(report)
    else:
        print("今日市場未發現符合條件之標的。")

if __name__ == "__main__":
    scan_market()