# webhook_server.py (Flask 기반 TradingView 신호 수신 서버)
from flask import Flask, request, jsonify
from trade_executor import execute_trade, handle_reverse_signal_with_switching
import json
import os

app = Flask(__name__)
STATUS_FILE = "trade_status.json"
SYMBOL = "BTCUSDT"


def save_trade_status(status):
    with open(STATUS_FILE, 'w') as f:
        json.dump(status, f)


def load_trade_status():
    if not os.path.exists(STATUS_FILE):
        return {"has_position": False}
    with open(STATUS_FILE, 'r') as f:
        return json.load(f)


@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json()
    signal = data.get("signal")  # 'buy' 또는 'sell'

    if signal not in ['buy', 'sell']:
        return jsonify({"error": "Invalid signal"}), 400

    print(f"📩 신호 수신: {signal}")
    status = load_trade_status()

    try:
        if status.get("has_position"):
            # 기존 포지션과 반대면 스위칭
            if signal != status.get("side"):
                print("🔄 반대 신호 감지 → 스위칭 진행")
                result = handle_reverse_signal_with_switching(SYMBOL, signal)
                save_trade_status({
                    "has_position": True,
                    "entry_price": result['entry_price'],
                    "quantity": result['quantity'],
                    "side": result['side'],
                    "tp1_hit": False,
                    "tp2_hit": False
                })
        else:
            result = execute_trade(signal, SYMBOL)
            save_trade_status({
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