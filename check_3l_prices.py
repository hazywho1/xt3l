"""
Part 4: XT.com 3L ETF Token Price Alert Bot — GitHub Actions version

This version is designed to run ONCE per execution (not loop forever),
because GitHub Actions triggers it on a schedule (every 5 minutes) rather
than keeping a process running continuously.

It reads your Telegram bot token and chat ID from environment variables
(set as GitHub Secrets), so no sensitive values are stored in this file.

Install requirements (handled automatically by the workflow file):
    pip install ccxt requests
"""

import os
import sys
import ccxt
import requests

# ---------------- CONFIG ----------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
ALERT_THRESHOLD_PERCENT = 100     # only alert on +100% or more (doubling)
# -----------------------------------------


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}
    response = requests.post(url, data=payload, timeout=10)
    if not response.ok:
        print(f"Telegram send failed: {response.text}")


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
            message = (
                f"🚨 <b>{symbol}</b> price alert!\n"
                f"24h change: <b>+{pct:.2f}%</b>\n"
                f"Last price: {last}\n"
                f"24h open: {open_price}"
            )
            send_telegram_message(message)
            alerts_sent += 1
            print(f"Alert sent for {symbol} (+{pct:.2f}%)")

    print(f"Check complete. {alerts_sent} alert(s) sent. "
          f"{len(tickers)} 3L tokens scanned.")


if __name__ == "__main__":
    main()
