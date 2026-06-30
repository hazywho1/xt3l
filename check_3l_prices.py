"""
Part 5: XT.com 3L ETF Token Price Alert Bot — with persistent state

Same as before, but now remembers which tokens are currently "in an
active alert" using a small JSON file (alerted_state.json) committed
back to the repo after each run. This prevents repeat alerts every
5 minutes while a token stays above +100% - you'll only get notified
once per spike, and again only if it drops back below the threshold
and crosses it again later.
"""

import os
import sys
import json
import ccxt
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ALERT_THRESHOLD_PERCENT = 100
STATE_FILE = "alerted_state.json"


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, data=payload, timeout=10)
    if not response.ok:
        print(f"Telegram send failed: {response.text}")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_state(alerted_symbols):
    with open(STATE_FILE, "w") as f:
        json.dump(sorted(alerted_symbols), f)


def get_xt_3l_tickers(exchange):
    tickers = exchange.fetch_tickers()
    three_l_tickers = {}
    for symbol, ticker in tickers.items():
        base = symbol.split("/")[0]
        if base.endswith("3L"):
            three_l_tickers[symbol] = ticker
    return three_l_tickers


def main():
    if not BOT_TOKEN or not CHAT_ID:
        print("ERROR: BOT_TOKEN or CHAT_ID environment variable is missing.")
        sys.exit(1)

    exchange = ccxt.xt({"enableRateLimit": True})
    exchange.load_markets()

    tickers = get_xt_3l_tickers(exchange)
    already_alerted = load_state()
    still_alerted = set()
    alerts_sent = 0

    for symbol, t in tickers.items():
        last = t.get("last")
        open_price = t.get("open")
        pct = t.get("percentage")

        if pct is None and last is not None and open_price not in (None, 0):
            pct = ((last - open_price) / open_price) * 100

        if pct is None:
            continue

        if pct >= ALERT_THRESHOLD_PERCENT:
            still_alerted.add(symbol)
            if symbol not in already_alerted:
                message = (
                    f"🚨 <b>{symbol}</b> price alert!\n"
                    f"24h change: <b>+{pct:.2f}%</b>\n"
                    f"Last price: {last}\n"
                    f"24h open: {open_price}"
                )
                send_telegram_message(message)
                alerts_sent += 1
                print(f"Alert sent for {symbol} (+{pct:.2f}%)")
        # if pct < threshold, we simply don't add it to still_alerted,
        # which means it's cleared and can alert again next time it spikes

    save_state(still_alerted)

    print(f"Check complete. {alerts_sent} new alert(s) sent. "
          f"{len(tickers)} 3L tokens scanned. "
          f"{len(still_alerted)} currently in alert state.")


if __name__ == "__main__":
    main()
