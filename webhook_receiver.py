"""
Standalone Webhook Receiver
=============================
Run alongside the Streamlit app:  python webhook_receiver.py
Listens on port 8502 for incoming TradingView / ChartInk HTTP POST signals.
Writes received signals to logs/webhook_signals.json for the Webhooks page to pick up.
"""

import json
import uuid
import logging
from datetime import datetime
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [WebhookServer] %(levelname)s %(message)s"
)
log = logging.getLogger("webhook_server")

SIGNAL_FILE = Path(__file__).parent / "logs" / "webhook_signals.json"
SIGNAL_FILE.parent.mkdir(exist_ok=True)
SECRET_TOKEN = ""   # Set to a secret string to validate X-Webhook-Token header; leave empty to disable

def _load():
    try:
        return json.loads(SIGNAL_FILE.read_text()) if SIGNAL_FILE.exists() else []
    except Exception:
        return []

def _save(signals):
    SIGNAL_FILE.write_text(json.dumps(signals, indent=2, default=str))


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info(fmt % args)

    def do_GET(self):
        if self.path == "/health":
            self._respond(200, {"status": "ok", "server": "groww_autotrader_webhook"})
        elif self.path == "/signals":
            self._respond(200, _load())
        else:
            self._respond(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/webhook":
            self._respond(404, {"error": "endpoint not found"})
            return

        # Validate secret token if configured
        if SECRET_TOKEN:
            token = self.headers.get("X-Webhook-Token", "")
            if token != SECRET_TOKEN:
                self._respond(401, {"error": "invalid token"})
                return

        try:
            length  = int(self.headers.get("Content-Length", 0))
            body    = self.rfile.read(length)
            payload = json.loads(body)
        except Exception as e:
            self._respond(400, {"error": f"invalid JSON: {e}"})
            return

        # Normalise and store signal
        signal = {
            "id":          str(uuid.uuid4())[:8],
            "received_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "action":      str(payload.get("action", payload.get("side", "BUY"))).upper(),
            "symbol":      str(payload.get("symbol", payload.get("ticker", "UNKNOWN"))),
            "exchange":    str(payload.get("exchange", "NSE")).upper(),
            "qty":         int(float(payload.get("qty", payload.get("quantity", payload.get("contracts", 1))))),
            "price":       float(payload.get("price", payload.get("ltp", 0))),
            "order_type":  str(payload.get("order_type", payload.get("type", "MARKET"))).upper(),
            "strategy":    str(payload.get("strategy", payload.get("strategy_name", "Webhook"))),
            "comment":     str(payload.get("comment", payload.get("message", ""))),
            "raw":         payload,
            "status":      "PENDING",
            "executed":    False,
            "error":       None,
        }

        signals = _load()
        signals.insert(0, signal)
        signals = signals[:500]   # keep last 500
        _save(signals)

        log.info("Signal received: %s %s qty=%s", signal["action"], signal["symbol"], signal["qty"])
        self._respond(200, {"status": "received", "id": signal["id"]})

    def _respond(self, code, data):
        body = json.dumps(data).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)


def run(port=8502):
    server = HTTPServer(("0.0.0.0", port), WebhookHandler)
    log.info("Webhook server running on http://0.0.0.0:%d", port)
    log.info("Signal endpoint:  POST http://localhost:%d/webhook", port)
    log.info("Health check:     GET  http://localhost:%d/health", port)
    log.info("Signal list:      GET  http://localhost:%d/signals", port)
    log.info("Signal file:      %s", SIGNAL_FILE)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("Webhook server stopped.")
        server.server_close()


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Groww AutoTrader – Webhook Receiver")
    p.add_argument("--port", type=int, default=8502, help="Port to listen on (default 8502)")
    p.add_argument("--token", type=str, default="", help="Secret token for X-Webhook-Token header")
    args = p.parse_args()
    SECRET_TOKEN = args.token
    run(args.port)
