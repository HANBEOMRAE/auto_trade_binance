# monitor_trade.py (Flask 서버용 실시간 모니터링 로직 - utils 제거)
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

SYMBOL = "BTCUSDT"
CHECK_INTERVAL = 1  # 1초 간격으로 실시간 확인
STATUS_FILE = "trade_status.json"


def save_trade_status(status):
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f)


def load_trade_status():
    if not os.path.exists(STATUS_FILE):
        return {"has_position": False}
    with open(STATUS_FILE, 'r') as f:
        return json.load(f)


def monitor_position():
    status = load_trade_status()
    if not status['has_position']:
        return

    entry_price = status['entry_price']
    side = status['side']
    quantity = status['quantity']

    try:
        current_price = float(client.futures_symbol_ticker(symbol=SYMBOL)['price'])
        change_pct = ((current_price - entry_price) / entry_price) * 100
        if side == 'sell':
            change_pct = -change_pct

        print(f"실시간 가격: {current_price}, 변동률: {change_pct:.2f}%")

        # 손절
        if change_pct <= STOP_LOSS:
            print("❌ 손절 조건 도달. 포지션 청산.")
            force_close_position(SYMBOL)
            save_trade_status({"has_position": False})
            return

        # 1차 익절
        if not status.get('tp1_hit') and change_pct >= TP1:
            print("✅ 1차 익절 조건 도달. 30% 청산.")
            # 청산 코드 생략 (예시 목적)
            status['tp1_hit'] = True
            status['stop_loss'] = TRAIL_SL
            save_trade_status(status)

        # 2차 익절
        elif status.get('tp1_hit') and not status.get('tp2_hit') and change_pct >= TP2:
            print("✅ 2차 익절 조건 도달. 50% 청산.")
            # 청산 코드 생략 (예시 목적)
            status['tp2_hit'] = True
            save_trade_status(status)

        # 익절 후 추적 손절
        elif status.get('tp1_hit') and change_pct <= TRAIL_SL:
            print("⚠️ 익절 후 손절 조건 도달. 잔여 포지션 전량 청산.")
            force_close_position(SYMBOL)
            save_trade_status({"has_position": False})
            return

    except Exception as e:
        print(f"❌ 모니터링 중 에러 발생: {e}")
        force_close_position(SYMBOL)
        save_trade_status({"has_position": False})


if __name__ == '__main__':
    while True:
        monitor_position()
        time.sleep(CHECK_INTERVAL)
