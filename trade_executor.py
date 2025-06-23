# trade_executor.py (AWS EC2 Flask 서버 배포에 맞춰 수정 - 텔레그램 코드 제거)
import os
import time
from binance.client import Client
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '.env'))

API_KEY = os.getenv("BINANCE_API_KEY")
API_SECRET = os.getenv("BINANCE_API_SECRET")
client = Client(API_KEY, API_SECRET)

# ✅ 거래 수수료 및 마진 비율 설정
LEVERAGE = 3
USE_RATIO = 0.98  # 증거금의 98% 사용


def execute_trade(signal, symbol):
    try:
        # 잔고 확인
        balance_data = client.futures_account_balance()
        usdt_balance = next((float(a['balance']) for a in balance_data if a['asset'] == 'USDT'), 0)

        # ✅ 자동 리밸런싱 조건: 잔고가 1000 이상이면 고정 100 USDT 사용
        if usdt_balance >= 1000:
            use_amount = 100
            print("💸 리밸런싱: 잔고 ≥ 1000 → 증거금 100 USDT 고정 사용")
        else:
            use_amount = usdt_balance * USE_RATIO

        # 마켓 가격 조회
        price = float(client.futures_symbol_ticker(symbol=symbol)['price'])

        # 수량 계산
        quantity = round((use_amount * LEVERAGE) / price, 3)

        # 레버리지 설정
        client.futures_change_leverage(symbol=symbol, leverage=LEVERAGE)

        # 주문 방향 설정
        side = Client.SIDE_BUY if signal == 'buy' else Client.SIDE_SELL

        # 시장가 주문
        order = client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=quantity,
            positionSide='BOTH'  # 단일 포지션 모드
        )

        entry_price = float(order['fills'][0]['price']) if 'fills' in order else price
        print(f"✅ {signal.upper()} 진입 완료 @ {entry_price} | 수량: {quantity}")

        return {
            'entry_price': entry_price,
            'quantity': quantity,
            'side': signal
        }

    except Exception as e:
        error_msg = f"❌ 거래 실행 실패: {e}"
        print(error_msg)
        raise


def force_close_position(symbol):
    try:
        # 현재 포지션 정보 조회
        positions = client.futures_position_information(symbol=symbol)
        pos = next(p for p in positions if p['symbol'] == symbol)

        qty = float(pos['positionAmt'])
        if qty == 0:
            return

        side = Client.SIDE_SELL if qty > 0 else Client.SIDE_BUY

        # 반대 방향 시장가 주문으로 청산
        client.futures_create_order(
            symbol=symbol,
            side=side,
            type='MARKET',
            quantity=abs(qty),
            reduceOnly=True,
            positionSide='BOTH'
        )

        print("🚨 포지션 강제 종료 완료")

    except Exception as e:
        error_msg = f"⚠️ 강제 종료 실패: {e}"
        print(error_msg)
        raise


def handle_reverse_signal_with_switching(symbol, signal):
    force_close_position(symbol)
    time.sleep(30)
    return execute_trade(signal, symbol)
