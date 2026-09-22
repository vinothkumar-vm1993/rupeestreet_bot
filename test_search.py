import requests

def search_indian_stocks(query: str):
    query = query.strip()
    headers = {"User-Agent": "Mozilla/5.0"}
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query}"
    try:
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            quotes = r.json().get("quotes", [])
            results = []
            for q in quotes:
                symbol = q.get("symbol", "")
                exch = q.get("exchange", "")
                name = q.get("shortname") or q.get("longname") or symbol
                # Filter to NSE/BSE
                if exch in ("NSI", "NSE", "BSE") or symbol.endswith(".NS") or symbol.endswith(".BO"):
                    clean_sym = symbol.replace(".NS", "").replace(".BO", "")
                    results.append({
                        "symbol": clean_sym,
                        "raw_ticker": symbol,
                        "name": name,
                        "exchange": "NSE" if (exch in ("NSI", "NSE") or symbol.endswith(".NS")) else "BSE"
                    })
            # Deduplicate by clean_sym
            seen = set()
            dedup = []
            for item in results:
                if item["symbol"] not in seen:
                    seen.add(item["symbol"])
                    dedup.append(item)
            return dedup[:8]
    except Exception as e:
        print("Search error:", e)
    return []

print("HDFC search results:")
for r in search_indian_stocks("hdfc"):
    print(" ", r)

print("\nTATA MOTORS search results:")
for r in search_indian_stocks("tata motors"):
    print(" ", r)

print("\nBEL search results:")
for r in search_indian_stocks("bel"):
    print(" ", r)
