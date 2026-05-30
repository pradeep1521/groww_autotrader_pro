"""
Example 3 – Option chain + basket order
=========================================
Fetches the NIFTY option chain, picks an ATM CE & PE pair,
and submits them as a basket order in a single API call.

Run from the project root:
    python kotak_neo_python/examples/03_option_chain_basket.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

from kotak_neo_python.kotak_neo import (
    KotakNeoClient, BasketOrder, Order,
    OrderSide, OrderType, ProductType, Exchange, Validity,
)


def main():
    client = KotakNeoClient(
        consumer_key = os.environ["KOTAK_CONSUMER_KEY"],
        username     = os.environ["KOTAK_USERNAME"],
        password     = os.environ["KOTAK_PASSWORD"],
        totp_seed    = os.environ["KOTAK_TOTP_SEED"],
    )
    client.login()

    # ── Option chain ──────────────────────────────────────────────────────
    chain = client.get_option_chain(symbol="NIFTY", expiry="27-Jun-2024")
    print(f"Fetched {len(chain)} option strikes for NIFTY 27-Jun-2024")

    # Pick first CE and PE for demonstration
    calls = [s for s in chain if s.get("optionType", "").upper() == "CE"][:1]
    puts  = [s for s in chain if s.get("optionType", "").upper() == "PE"][:1]

    legs = []
    for strike in calls + puts:
        legs.append(Order(
            exchange       = Exchange.NFO,
            trading_symbol = strike.get("trdSym", strike.get("symbol", "")),
            side           = OrderSide.BUY,
            order_type     = OrderType.MARKET,
            product        = ProductType.NRML,
            quantity       = int(strike.get("lot_size", 50)),
        ))

    if not legs:
        print("No strikes found – exiting without placing basket.")
        return

    basket = BasketOrder(name="NIFTY_ATM_Straddle", orders=legs)
    responses = client.place_basket_order(basket)
    for resp in responses:
        print(f"  Leg order_id={resp.order_id}  status={resp.status}")

    client.logout()


if __name__ == "__main__":
    main()
