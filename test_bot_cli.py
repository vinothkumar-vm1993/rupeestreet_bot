#!/usr/bin/env python3
"""
RUPEESTREET // INTERACTIVE CONSOLE EMULATOR
Simulates the Telegram Bot directly in the terminal without requiring BotFather token.
"""
import sys
import engines

def strip_html(text: str) -> str:
    """Simple tag stripper for terminal readability."""
    import re
    return re.sub(r'<[^>]*>', '', text)

def print_banner():
    print("=" * 65)
    print("  🏛️  RUPEESTREET // TELEGRAM BOT SIMULATION CONSOLE")
    print("  Status: ACTIVE | Clearance: UNRESTRICTED")
    print("=" * 65)
    print("Available Directives:")
    print("  1. regime             -> View Market Regime & Macro Report")
    print("  2. research <SYMBOL>  -> Single-Stock Institutional Report (e.g. research HDFCBANK)")
    print("  3. risk               -> Risk Committee Charter & Gating Limits")
    print("  4. portfolio          -> Portfolio Allocation & Cash Buffer")
    print("  5. watchlist          -> Active Monitored Watchlist")
    print("  6. track <SYMBOL>     -> Position Risk Tracker")
    print("  7. alert <MSG>        -> Broadcast Urgent Risk Alert")
    print("  8. exit / quit        -> Exit console")
    print("=" * 65)

def main():
    print_banner()
    while True:
        try:
            cmd_raw = input("\n[RUPEESTREET-PROMPT] > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nShutting down RUPEESTREET console.")
            break

        if not cmd_raw:
            continue

        parts = cmd_raw.split()
        directive = parts[0].lower().lstrip("/")

        if directive in ("exit", "quit", "q"):
            print("Console closed.")
            break
        elif directive in ("start", "help", "menu"):
            print_banner()
        elif directive == "regime":
            print("\n" + strip_html(engines.get_market_regime_report()))
        elif directive == "research":
            sym = parts[1] if len(parts) > 1 else "HDFCBANK"
            print("\n" + strip_html(engines.get_stock_research_report(sym)))
        elif directive == "risk":
            print("\n" + strip_html(engines.get_risk_summary()))
        elif directive == "portfolio":
            print("\n" + strip_html(engines.get_portfolio_status()))
        elif directive == "watchlist":
            print("\n" + strip_html(engines.get_active_watchlist()))
        elif directive == "track":
            sym = parts[1] if len(parts) > 1 else "HDFCBANK"
            sec = engines.TitanMarketData.SECURITIES.get(sym.upper())
            if not sec:
                print(f"Asset {sym} not in tracked positions.")
            else:
                msg = f"""🎯 RUPEESTREET // POSITION RISK MONITOR: {sym.upper()}
• Current Spot: {sec['price']}
• Entry Level: {sec['entry']}
• Hard Stop Loss: {sec['stop_loss']} (NON-NEGOTIABLE)
• Targets: {', '.join(sec['targets'])}
• Allocated Risk Budget: 0.42% NAV (Compliant <= 1.0%)
• Position Status: IN ACCUMULATION / DISCIPLINED HOLD"""
                print("\n" + msg)
        elif directive == "alert":
            alert_msg = " ".join(parts[1:]) if len(parts) > 1 else "Systemic Volatility Compression Warning."
            print(f"\n🚨 URGENT RISK ALERT BROADCAST:\n{alert_msg}")
        else:
            print(f"Unknown command: '{directive}'. Type 'help' to view available directives.")

if __name__ == "__main__":
    main()
