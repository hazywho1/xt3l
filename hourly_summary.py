"""
Hourly Top 3L Gainers Summary Bot

Fetches all 3L ETF tokens on XT.com, sorts them by 24h price change
(highest first), and sends a Telegram message with the top 10 gainers.
Runs once per hour via GitHub Actions.
"""

import os
import sys
import ccxt
import requests

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")
TOP_N = 3  # number of top gainers to show


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

    # Build a list of (symbol, pct, last_price) for all tokens with valid data
    results = []
    for symbol, t in tickers.items():
        last = t.get("last")
        open_price = t.get("open")
        pct = t.get("percentage")

        if pct is None and last is not None and open_price not in (None, 0):
            pct = ((last - open_price) / open_price) * 100

        if pct is not None and last is not None:
            results.append((symbol, pct, last))

    # Sort by 24h change, highest first
    results.sort(key=lambda x: x[1], reverse=True)
    top = results[:TOP_N]

    if not top:
        print("No data available to send.")
        return

    # Build the Telegram message
    lines = ["📊 <b>Hourly Top 3L ETF Gainers on XT.com</b>\n"]
    medals = ["🥇", "🥈", "🥉"]

    for i, (symbol, pct, last) in enumerate(top):
        medal = medals[i] if i < 3 else f"{i+1}."
        sign = "+" if pct >= 0 else ""
        lines.append(f"{medal} <b>{symbol}</b>")
        lines.append(f"   24h change: <b>{sign}{pct:.2f}%</b>  |  Price: {last}\n")

    message = "\n".join(lines)
    send_telegram_message(message)
    print(f"Hourly summary sent. Top gainer: {top[0][0]} ({top[0][1]:+.2f}%)")


if __name__ == "__main__":
    main()
