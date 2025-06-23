# monitor_trade.py (webhook에서 전달된 심볼 기반 실시간 모니터링)
import os
import json
import time
from binance.client import Client
from dotenv import load_dotenv
from trade_executor import force_close_position

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
client = Client(API_KEY, API_SECRET)

# 손절 및 익절 기준 설정
STOP_LOSS = -0.5    # 손절 -0.5%
TP1 = 0.5           # 1차 익절 +0.5%
TP2 = 1.1           # 2차 익절 +1.1%
TRAIL_SL = 0.1      # 익절 후 손절 -0.1%

CHECK_INTERVAL = 1  # 1초 간격으로 실시간 확인

TRADE_DIR = "trade_status"
os.makedirs(TRADE_DIR, exist_ok=True)

def status_filename(symbol):
    return os.path.join(TRADE_DIR, f"{symbol}_trade_status.json")

def get_all_symbols():
    files = os.listdir(TRADE_DIR)
    return [f.replace('_trade_status.json', '') for f in files if f.endswith('_trade_status.json')]

def save_trade_status(symbol, status):
    with open(status_filename(symbol), 'w') as f:
        json.dump(status, f)

def load_trade_status(symbol):
    path = status_filename(symbol)
    if not os.path.exists(path):
        return {"has_position": False}
    with open(path, 'r') as f:
        return json.load(f)

def monitor_position(symbol):
    status = load_trade_status(symbol)
    if not status['has_position']:
        return

    entry_price = status['entry_price']
    side = status['side']
    quantity = status['quantity']

    try:
        current_price = float(client.futures_symbol_ticker(symbol=symbol)['price'])
        change_pct = ((current_price - entry_price) / entry_price) * 100
        if side == 'sell':
            change_pct = -change_pct

        print(f"[{symbol}] 실시간 가격: {current_price}, 변동률: {change_pct:.2f}%")

        # 손절
        if change_pct <= STOP_LOSS:
            print(f"[{symbol}] ❌ 손절 조건 도달. 포지션 청산.")
            force_close_position(symbol)
            save_trade_status(symbol, {"has_position": False})
            return

        # 1차 익절
        if not status.get('tp1_hit') and change_pct >= TP1:
            print(f"[{symbol}] ✅ 1차 익절 조건 도달. 30% 청산.")
            status['tp1_hit'] = True
            status['stop_loss'] = TRAIL_SL
            save_trade_status(symbol, status)

        # 2차 익절
        elif status.get('tp1_hit') and not status.get('tp2_hit') and change_pct >= TP2:
            print(f"[{symbol}] ✅ 2차 익절 조건 도달. 50% 청산.")
            status['tp2_hit'] = True
            save_trade_status(symbol, status)

        # 익절 후 추적 손절
        elif status.get('tp1_hit') and change_pct <= TRAIL_SL:
            print(f"[{symbol}] ⚠️ 익절 후 손절 조건 도달. 잔여 포지션 전량 청산.")
            force_close_position(symbol)
            save_trade_status(symbol, {"has_position": False})
            return

    except Exception as e:
        print(f"[{symbol}] ❌ 모니터링 중 에러 발생: {e}")
        force_close_position(symbol)
        save_trade_status(symbol, {"has_position": False})


if __name__ == '__main__':
    while True:
        for symbol in get_all_symbols():
            monitor_position(symbol)
        time.sleep(CHECK_INTERVAL)
