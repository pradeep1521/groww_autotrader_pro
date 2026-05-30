"""
Example 4 – Using Kotak Neo through the BrokerFactory
=======================================================
Shows how to swap in kotak_neo through the same AbstractBroker
interface that every other broker uses.

Run from the project root:
    python kotak_neo_python/examples/04_broker_factory.py
"""
import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from brokers.broker_factory import BrokerFactory
from brokers.abstract_broker import BrokerOrder


def main():
    print("Available brokers:", BrokerFactory.get_available_brokers())

    # Authenticate using env vars (no credentials dict needed)
    success, msg = BrokerFactory.setup_global_broker("kotak_neo", credentials={})
    print(msg)
    if not success:
        return

    broker = BrokerFactory.get_global_broker()

    # Balance
    balance = broker.get_balance()
    print(f"Available cash : ₹{balance.available_cash:,.2f}")

    # Positions
    positions = broker.get_positions()
    print(f"Open positions : {len(positions)}")
    for p in positions:
        print(f"  {p.symbol:<20} qty={p.quantity}  PnL=₹{p.pnl:,.2f}")

    # Quote
    quote = broker.get_quote("RELIANCE-EQ")
    print(f"RELIANCE LTP   : ₹{quote.get('ltp', 'N/A')}")

    # Paper order (won't fire in paper mode)
    order = BrokerOrder(
        symbol     = "RELIANCE-EQ",
        side       = "BUY",
        quantity   = 1,
        order_type = "MARKET",
        product    = "MIS",
        price      = 0.0,
    )
    ok, msg, order_id = broker.place_order(order)
    print(f"Order: {ok} | {msg} | id={order_id}")

    broker.logout() if hasattr(broker, "logout") else None


if __name__ == "__main__":
    main()
