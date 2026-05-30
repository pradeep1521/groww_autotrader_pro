"""
Example 1 – Basic order placement with Kotak Neo (₹0 brokerage)
================================================================
Run from the project root:
    python kotak_neo_python/examples/01_place_order.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from kotak_neo_python.kotak_neo import (
    KotakNeoClient, Order, OrderSide, OrderType,
    ProductType, Exchange, Validity,
)

def main():
    client = KotakNeoClient(
        consumer_key = os.environ["KOTAK_CONSUMER_KEY"],
        username     = os.environ["KOTAK_USERNAME"],
        password     = os.environ["KOTAK_PASSWORD"],
        totp_seed    = os.environ["KOTAK_TOTP_SEED"],
    )
    client.login()
    print("✅ Authenticated with Kotak Neo")

    # ── Margin / balance ──────────────────────────────────────────────────
    margin = client.get_margins()
    print(f"Available cash : ₹{margin.available_cash:,.2f}")
    print(f"Used margin    : ₹{margin.used_margin:,.2f}")

    # ── Live quote ────────────────────────────────────────────────────────
    quotes = client.get_quote(["NSE:RELIANCE-EQ"])
    if quotes:
        print(f"RELIANCE LTP   : ₹{quotes[0].ltp}")

    # ── Place a paper / test MARKET order ─────────────────────────────────
    order = Order(
        exchange       = Exchange.NSE,
        trading_symbol = "RELIANCE-EQ",
        side           = OrderSide.BUY,
        order_type     = OrderType.MARKET,
        product        = ProductType.MIS,   # intraday
        quantity       = 1,
    )
    resp = client.place_order(order)
    print(f"Order ID : {resp.order_id}  Status : {resp.status}")

    client.logout()

if __name__ == "__main__":
    main()
