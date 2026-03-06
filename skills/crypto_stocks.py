"""
Crypto & Stocks skill — get live prices from Telegram.
No API keys needed. Uses free public APIs:
  • CoinGecko (crypto) — no key, 30 calls/min
  • Yahoo Finance via query2 (stocks) — no key, unlimited
"""
import requests

SKILL_INFO = {
    "name": "crypto_stocks",
    "description": "Get live crypto and stock prices — Bitcoin, Ethereum, TSLA, AAPL, etc.",
    "version": "1.0",
    "icon": "💰",
    "author": "ninoclaw",
    "requires_key": False,
}

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "crypto_price",
            "description": "Get the current price of a cryptocurrency. Examples: 'bitcoin price', 'how much is ETH', 'BNB price', 'solana price'",
            "parameters": {
                "type": "object",
                "properties": {
                    "coin": {"type": "string", "description": "Cryptocurrency name or symbol, e.g. 'bitcoin', 'ethereum', 'BTC', 'SOL'"},
                },
                "required": ["coin"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "stock_price",
            "description": "Get the current stock price. Examples: 'TSLA stock', 'Apple stock price', 'AAPL price', 'RELIANCE stock'",
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {"type": "string", "description": "Stock ticker symbol, e.g. 'TSLA', 'AAPL', 'GOOGL', 'RELIANCE.NS' (add .NS for NSE India)"},
                },
                "required": ["symbol"],
            },
        },
    },
]

# ── Common crypto name → CoinGecko ID mapping ───────────────────────────────

_CRYPTO_MAP = {
    "btc": "bitcoin", "bitcoin": "bitcoin",
    "eth": "ethereum", "ethereum": "ethereum",
    "bnb": "binancecoin", "binance": "binancecoin",
    "sol": "solana", "solana": "solana",
    "ada": "cardano", "cardano": "cardano",
    "xrp": "ripple", "ripple": "ripple",
    "dot": "polkadot", "polkadot": "polkadot",
    "doge": "dogecoin", "dogecoin": "dogecoin",
    "shib": "shiba-inu", "shiba": "shiba-inu",
    "avax": "avalanche-2", "avalanche": "avalanche-2",
    "matic": "matic-network", "polygon": "matic-network",
    "link": "chainlink", "chainlink": "chainlink",
    "atom": "cosmos", "cosmos": "cosmos",
    "uni": "uniswap", "uniswap": "uniswap",
    "ltc": "litecoin", "litecoin": "litecoin",
    "ton": "the-open-network", "toncoin": "the-open-network",
    "trx": "tron", "tron": "tron",
    "pepe": "pepe",
    "sui": "sui",
    "apt": "aptos", "aptos": "aptos",
    "near": "near", "near protocol": "near",
    "pi": "pi-network", "pi network": "pi-network",
}

# ── Common stock name → ticker mapping ───────────────────────────────────────

_STOCK_MAP = {
    "apple": "AAPL", "tesla": "TSLA", "google": "GOOGL",
    "microsoft": "MSFT", "amazon": "AMZN", "meta": "META",
    "nvidia": "NVDA", "netflix": "NFLX", "amd": "AMD",
    "intel": "INTC", "disney": "DIS", "boeing": "BA",
    "reliance": "RELIANCE.NS", "tcs": "TCS.NS", "infosys": "INFY.NS",
    "wipro": "WIPRO.NS", "hdfc": "HDFCBANK.NS", "sbi": "SBIN.NS",
    "tatamotors": "TATAMOTORS.NS", "tata motors": "TATAMOTORS.NS",
    "adani": "ADANIENT.NS", "bajaj": "BAJFINANCE.NS",
    "icici": "ICICIBANK.NS", "kotak": "KOTAKBANK.NS",
    "nifty": "^NSEI", "sensex": "^BSESN",
}


def _crypto_price(coin):
    coin = coin.lower().strip()
    coin_id = _CRYPTO_MAP.get(coin, coin)

    try:
        url = f"https://api.coingecko.com/api/v3/simple/price"
        params = {
            "ids": coin_id,
            "vs_currencies": "usd,inr",
            "include_24hr_change": "true",
            "include_market_cap": "true",
        }
        r = requests.get(url, params=params, timeout=10,
                         headers={"Accept": "application/json"})
        r.raise_for_status()
        data = r.json()

        if coin_id not in data:
            return f"❌ Cryptocurrency '{coin}' not found. Try the full name (e.g. 'bitcoin', 'ethereum')."

        info = data[coin_id]
        usd = info.get("usd", 0)
        inr = info.get("inr", 0)
        change = info.get("usd_24h_change", 0)
        mcap = info.get("usd_market_cap", 0)

        arrow = "📈" if change >= 0 else "📉"
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"

        # Format market cap
        if mcap >= 1e12:
            mcap_str = f"${mcap/1e12:.2f}T"
        elif mcap >= 1e9:
            mcap_str = f"${mcap/1e9:.2f}B"
        elif mcap >= 1e6:
            mcap_str = f"${mcap/1e6:.2f}M"
        else:
            mcap_str = f"${mcap:,.0f}"

        return (
            f"{arrow} **{coin_id.replace('-', ' ').title()}**\n"
            f"💵 ${usd:,.2f} USD\n"
            f"🇮🇳 ₹{inr:,.2f} INR\n"
            f"📊 24h: {change_str}\n"
            f"🏦 Market Cap: {mcap_str}"
        )
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 429:
            return "⚠️ Rate limited by CoinGecko. Try again in a minute."
        return f"❌ CoinGecko API error: {e}"
    except Exception as e:
        return f"❌ Crypto error: {e}"


def _stock_price(symbol):
    symbol = symbol.strip()
    # Check common name mapping
    mapped = _STOCK_MAP.get(symbol.lower())
    if mapped:
        symbol = mapped
    symbol = symbol.upper()

    try:
        url = f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}"
        params = {"range": "1d", "interval": "1m"}
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(url, params=params, headers=headers, timeout=10)
        r.raise_for_status()
        data = r.json()

        result = data.get("chart", {}).get("result", [])
        if not result:
            return f"❌ Stock '{symbol}' not found. For Indian stocks, add .NS (e.g. RELIANCE.NS)."

        meta = result[0].get("meta", {})
        price = meta.get("regularMarketPrice", 0)
        prev_close = meta.get("previousClose", 0) or meta.get("chartPreviousClose", 0)
        currency = meta.get("currency", "USD")
        name = meta.get("shortName", symbol)
        exchange = meta.get("exchangeName", "")

        # Calculate change
        if prev_close and prev_close > 0:
            change = price - prev_close
            change_pct = (change / prev_close) * 100
        else:
            change = 0
            change_pct = 0

        arrow = "📈" if change >= 0 else "📉"
        change_str = f"+{change:.2f}" if change >= 0 else f"{change:.2f}"
        pct_str = f"+{change_pct:.2f}%" if change_pct >= 0 else f"{change_pct:.2f}%"

        # Currency symbol
        curr_sym = "₹" if currency == "INR" else "$" if currency == "USD" else currency + " "

        return (
            f"{arrow} **{name}** ({symbol})\n"
            f"💵 {curr_sym}{price:,.2f}\n"
            f"📊 Change: {change_str} ({pct_str})\n"
            f"🏛️ {exchange} · {currency}"
        )
    except requests.HTTPError as e:
        return f"❌ Yahoo Finance error: {e}"
    except Exception as e:
        return f"❌ Stock error: {e}"


def execute(tool_name, arguments):
    try:
        if tool_name == "crypto_price":
            return _crypto_price(arguments.get("coin", ""))
        elif tool_name == "stock_price":
            return _stock_price(arguments.get("symbol", ""))
    except Exception as e:
        return f"❌ Error: {e}"
    return None
