# webhook_server.py (Flask 기반 TradingView 신호 수신 서버 - symbol 동적 처리)
from flask import Flask, request, jsonify
from trade_executor import execute_trade, handle_reverse_signal_with_switching
import json
import os

app = Flask(__name__)
STATUS_FILE = "trade_status.json"


def save_trade_status(symbol, status):
    with open(f"{symbol}_{STATUS_FILE}", 'w') as f:
        json.dump(status, f)


def load_trade_status(symbol):
    file_path = f"{symbol}_{STATUS_FILE}"
    if not os.path.exists(file_path):
        return {"has_position": False}
    with open(file_path, 'r') as f:
        return json.load(f)


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    signal = data.get("signal")      # 'buy' 또는 'sell'
    symbol = data.get("symbol")      # 예: 'BTCUSDT'

    if signal not in ['buy', 'sell'] or not symbol:
        return jsonify({"error": "Invalid signal or symbol"}), 400

    print(f"📩 신호 수신: {signal} / 심볼: {symbol}")
    status = load_trade_status(symbol)

    try:
        if status.get("has_position"):
            if signal != status.get("side"):
                print("🔄 반대 신호 감지 → 스위칭 진행")
                result = handle_reverse_signal_with_switching(symbol, signal)
                save_trade_status(symbol, {
                    "has_position": True,
                    "entry_price": result['entry_price'],
                    "quantity": result['quantity'],
                    "side": result['side'],
                    "tp1_hit": False,
                    "tp2_hit": False
                })
        else:
            result = execute_trade(signal, symbol)
            save_trade_status(symbol, {
                "has_position": True,
                "entry_price": result['entry_price'],
                "quantity": result['quantity'],
                "side": result['side'],
                "tp1_hit": False,
                "tp2_hit": False
            })

        return jsonify({"status": "success"})

    except Exception as e:
        print(f"❌ 거래 중 에러 발생: {e}")
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)