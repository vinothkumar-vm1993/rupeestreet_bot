import difflib
import requests

# Master dictionary of common Indian Equities & Conglomerate Groups
GROUP_DIRECTORY = {
    "JIO": {
        "title": "Jio / Reliance Group",
        "stocks": [
            {"symbol": "JIOFIN", "name": "Jio Financial Services Ltd", "tier": "₹200 Budget"},
            {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "tier": "₹1,000 Budget"},
        ]
    },
    "HDFC": {
        "title": "HDFC Group",
        "stocks": [
            {"symbol": "HDFCBANK", "name": "HDFC Bank Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "HDFCLIFE", "name": "HDFC Life Insurance Co Ltd", "tier": "₹500 Budget"},
            {"symbol": "HDFCAMC", "name": "HDFC Asset Management Co Ltd", "tier": "₹5,000+ Budget"},
        ]
    },
    "TATA": {
        "title": "Tata Group",
        "stocks": [
            {"symbol": "TMPV", "name": "Tata Motors Passenger Vehicles Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "TMCV", "name": "Tata Motors Commercial Vehicles Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "TATAPOWER", "name": "Tata Power Co Ltd", "tier": "₹500 Budget"},
            {"symbol": "TATASTEEL", "name": "Tata Steel Ltd", "tier": "₹200 Budget"},
            {"symbol": "TCS", "name": "Tata Consultancy Services Ltd", "tier": "₹5,000+ Budget"},
            {"symbol": "TATACONSUM", "name": "Tata Consumer Products Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "TATACOMM", "name": "Tata Communications Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "TATACHEM", "name": "Tata Chemicals Ltd", "tier": "₹1,000 Budget"},
        ]
    },
    "TATAMOTORS": {
        "title": "Tata Motors Demerger Entities",
        "stocks": [
            {"symbol": "TMPV", "name": "Tata Motors Passenger Vehicles Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "TMCV", "name": "Tata Motors Commercial Vehicles Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "TATAPOWER", "name": "Tata Power (EV Charging Partner)", "tier": "₹500 Budget"},
        ]
    },
    "SBI": {
        "title": "State Bank of India Group",
        "stocks": [
            {"symbol": "SBIN", "name": "State Bank of India (PSU Banking Leader)", "tier": "₹1,000 Budget"},
            {"symbol": "SBILIFE", "name": "SBI Life Insurance Co Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "SBICARD", "name": "SBI Cards & Payment Services Ltd", "tier": "₹500 Budget"},
        ]
    },
    "RELIANCE": {
        "title": "Reliance Group",
        "stocks": [
            {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "JIOFIN", "name": "Jio Financial Services Ltd", "tier": "₹200 Budget"},
        ]
    },
    "ADANI": {
        "title": "Adani Group",
        "stocks": [
            {"symbol": "ADANIENT", "name": "Adani Enterprises Ltd", "tier": "₹5,000+ Budget"},
            {"symbol": "ADANIPORTS", "name": "Adani Ports & Special Economic Zone", "tier": "₹1,000 Budget"},
            {"symbol": "ADANIPOWER", "name": "Adani Power Ltd", "tier": "₹500 Budget"},
            {"symbol": "ADANIGREEN", "name": "Adani Green Energy Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "ATGL", "name": "Adani Total Gas Ltd", "tier": "₹500 Budget"},
        ]
    },
    "BAJAJ": {
        "title": "Bajaj Group",
        "stocks": [
            {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "tier": "₹5,000+ Budget"},
            {"symbol": "BAJAJFINSV", "name": "Bajaj Finserv Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "BAJAJ-AUTO", "name": "Bajaj Auto Ltd", "tier": "₹5,000+ Budget"},
        ]
    },
    "ICICI": {
        "title": "ICICI Group",
        "stocks": [
            {"symbol": "ICICIBANK", "name": "ICICI Bank Ltd", "tier": "₹1,000 Budget"},
            {"symbol": "ICICIPRULI", "name": "ICICI Prudential Life Insurance Co", "tier": "₹500 Budget"},
            {"symbol": "ICICIGI", "name": "ICICI Lombard General Insurance Co", "tier": "₹1,000 Budget"},
        ]
    },
    "INFOSYS": {
        "title": "Infosys",
        "stocks": [
            {"symbol": "INFY", "name": "Infosys Ltd (IT Services)", "tier": "₹1,000 Budget"}
        ]
    },
    "L&T": {
        "title": "Larsen & Toubro Group",
        "stocks": [
            {"symbol": "LT", "name": "Larsen & Toubro Ltd", "tier": "₹5,000+ Budget"},
            {"symbol": "LTIM", "name": "LTIMindtree Ltd", "tier": "₹5,000+ Budget"},
        ]
    }
}

# Known tickers dictionary for instant fuzzy typo check
KNOWN_TICKERS = [
    "BEL", "NHPC", "IOC", "IDFCFIRSTB", "SAIL", "BHEL", "NTPC", "ONGC",
    "TATASTEEL", "GAIL", "ZOMATO", "PNB", "ASHOKLEY", "CANBK", "FEDERALBNK",
    "TATAPOWER", "WIPRO", "HINDALCO", "ITC", "VEDL", "COALINDIA", "POWERGRID",
    "ICICIBANK", "AXISBANK", "HDFCBANK", "RELIANCE", "JIOFIN", "INFY", "SBIN",
    "TMPV", "TMCV", "BAJAJFINSV", "MARUTI", "LTIM", "ULTRACEMCO", "TCS", "LT",
    "BAJFINANCE", "HDFCLIFE", "HDFCAMC", "SBILIFE", "SBICARD"
]

def resolve_input_with_fuzzy(query: str):
    """
    Intelligent Search & Suggestion Engine:
    1. Exact Group Match (e.g. 'JIO', 'TATA', 'HDFC', 'SBI', 'ADANI')
    2. Exact Ticker Match (e.g. 'BEL', 'TATAPOWER', 'JIOFIN', 'INFY')
    3. Ticker Prefix Matches (e.g. 'JIO' -> 'JIOFIN', 'TATP' -> 'TATAPOWER')
    4. Group Substring / Fuzzy Matches (e.g. 'HFC' -> 'HDFC', 'TAT' -> 'TATA')
    5. Live Yahoo Search API query for real NSE/BSE securities
    6. Strict Typo Tolerance (only for strings >= 5 chars, NEVER for short acronyms like JIO)
    7. NOT_FOUND fallback (Never return a completely unrelated stock)
    """
    q_clean = query.strip().upper().replace(" ", "")
    if not q_clean:
        return ("NOT_FOUND", "", None)

    # 1. Exact Group Match (e.g. JIO, TATA, HDFC, SBI, ADANI)
    if q_clean in GROUP_DIRECTORY:
        return ("GROUP_MATCH", q_clean, GROUP_DIRECTORY[q_clean]["stocks"])

    # 2. Exact Ticker Match (e.g. BEL, TATAPOWER, JIOFIN, INFY)
    if q_clean in KNOWN_TICKERS:
        return ("EXACT", q_clean, None)

    # 3. Ticker Prefix Matches (e.g. 'JIO' starts 'JIOFIN')
    prefix_tickers = [t for t in KNOWN_TICKERS if t.startswith(q_clean)]
    if prefix_tickers:
        if len(prefix_tickers) == 1 and prefix_tickers[0] == q_clean:
            return ("EXACT", prefix_tickers[0], None)
        suggs = [{"symbol": t, "name": f"NSE: {t}", "tier": "Tracked Bracket"} for t in prefix_tickers]
        return ("TYPO_SUGGESTION", q_clean, suggs)

    # 4. Group Substring / Fuzzy Match (e.g. 'HFC' -> 'HDFC')
    group_keys = list(GROUP_DIRECTORY.keys())
    sub_groups = [g for g in group_keys if q_clean in g or g.startswith(q_clean)]
    if sub_groups:
        matched_g = sub_groups[0]
        return ("GROUP_MATCH", matched_g, GROUP_DIRECTORY[matched_g]["stocks"])

    if len(q_clean) >= 3:
        close_groups = difflib.get_close_matches(q_clean, group_keys, n=1, cutoff=0.65)
        if close_groups:
            matched_g = close_groups[0]
            return ("TYPO_SUGGESTION", matched_g, GROUP_DIRECTORY[matched_g]["stocks"])

    # 5. Live Yahoo Search API query
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        url = f"https://query2.finance.yahoo.com/v1/finance/search?q={query.strip()}"
        r = requests.get(url, headers=headers, timeout=5)
        if r.status_code == 200:
            quotes = r.json().get("quotes", [])
            matches = []
            for q in quotes:
                sym = q.get("symbol", "")
                exch = q.get("exchange", "")
                name = q.get("shortname") or q.get("longname") or sym
                if exch in ("NSI", "NSE", "BSE") or sym.endswith(".NS") or sym.endswith(".BO"):
                    clean_s = sym.replace(".NS", "").replace(".BO", "")
                    if not any(m["symbol"] == clean_s for m in matches):
                        matches.append({
                            "symbol": clean_s,
                            "name": name,
                            "tier": "NSE/BSE Listed"
                        })
            if matches:
                exact_live = [m for m in matches if m["symbol"] == q_clean]
                if exact_live:
                    return ("EXACT", exact_live[0]["symbol"], None)
                return ("GROUP_MATCH", q_clean, matches[:6])
    except Exception:
        pass

    # 6. Strict Typo Tolerance on Tickers (ONLY for strings >= 5 chars, NEVER for 3-letter codes)
    if len(q_clean) >= 5:
        close_tickers = difflib.get_close_matches(q_clean, KNOWN_TICKERS, n=3, cutoff=0.75)
        if close_tickers:
            suggs = [{"symbol": t, "name": f"NSE: {t}", "tier": "Suggested Match"} for t in close_tickers]
            return ("TYPO_SUGGESTION", close_tickers[0], suggs)

    # 7. Safe Fallback: NOT_FOUND (Never substitute an unrelated stock like IOC for JIO!)
    return ("NOT_FOUND", q_clean, None)


def resolve_symbol_or_suggestions(query: str):
    """Convenience helper mapping search output to (EXACT/SUGGESTIONS/NOT_FOUND, payload)."""
    mtype, matched_entity, payload = resolve_input_with_fuzzy(query)
    if mtype in ("GROUP_MATCH", "TYPO_SUGGESTION"):
        return ("SUGGESTIONS", payload)
    elif mtype == "EXACT":
        return ("EXACT", matched_entity)
    else:
        return ("NOT_FOUND", matched_entity)


