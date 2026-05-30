"""
Example 2 – Live WebSocket tick streaming
==========================================
Subscribes to RELIANCE and TCS and prints each tick for 30 seconds.

Run from the project root:
    python kotak_neo_python/examples/02_websocket_stream.py
"""
import os
import time
from dotenv import load_dotenv
load_dotenv()

from kotak_neo_python.kotak_neo import KotakNeoClient, KotakNeoWebSocket


def main():
    client = KotakNeoClient(
        consumer_key = os.environ["KOTAK_CONSUMER_KEY"],
        username     = os.environ["KOTAK_USERNAME"],
        password     = os.environ["KOTAK_PASSWORD"],
        totp_seed    = os.environ["KOTAK_TOTP_SEED"],
    )
    client.login()
    print("✅ Logged in – starting WebSocket stream")

    ws = KotakNeoWebSocket(client)

    # ── Callbacks ─────────────────────────────────────────────────────────
    ws.on_tick  = lambda tick: print(
        f"TICK  {tick['symbol']:<20} LTP={tick['ltp']:>10.2f}"
        f"  Vol={tick['volume']:>12,}"
    )
    ws.on_order = lambda msg: print(f"ORDER UPDATE: {msg}")
    ws.on_error = lambda e:   print(f"⚠️  WS error: {e}")
    ws.on_open  = lambda:     print("🟢 WebSocket connected")
    ws.on_close = lambda:     print("🔴 WebSocket closed")

    # ── Subscribe to tokens (exchange_segment|instrument_token) ───────────
    ws.subscribe(["nse_cm|2885", "nse_cm|11536"])  # RELIANCE, TCS

    ws.connect(block=False)   # background thread

    print("Streaming for 30 seconds… (Ctrl+C to exit early)")
    try:
        time.sleep(30)
    except KeyboardInterrupt:
        pass
    finally:
        ws.disconnect()
        client.logout()
        print("Done.")


if __name__ == "__main__":
    main()
