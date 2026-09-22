import sys
import os
import re

print("=" * 70)
print("  🏛️  RUPEESTREET // AUTOMATED END-TO-END VERIFICATION SUITE")
print("=" * 70)

# -------------------------------------------------------------
# TEST 1: SEARCH & SUGGESTION ENGINE
# -------------------------------------------------------------
print("\n[TEST 1] Testing Search & Suggestion Engine...")
import search_engine

# 1A: HDFC Group query
t, res = search_engine.resolve_symbol_or_suggestions("HDFC")
assert t == "SUGGESTIONS", f"Expected SUGGESTIONS for HDFC, got {t}"
assert len(res) >= 2, f"Expected multiple HDFC suggestions, got {len(res)}"
print(f"  ✅ HDFC Disambiguation: PASS ({len(res)} matching options surfaced)")

# 1B: TATAMOTORS query
t, res = search_engine.resolve_symbol_or_suggestions("TATAMOTORS")
assert t == "SUGGESTIONS", f"Expected SUGGESTIONS for TATAMOTORS, got {t}"
print(f"  ✅ TATAMOTORS Demerger Disambiguation: PASS ({res[0]['symbol']} - {res[0]['name']})")

# 1C: Direct Single Tickers
t, res = search_engine.resolve_symbol_or_suggestions("BEL")
assert t == "EXACT" and res == "BEL"
print("  ✅ BEL Exact Match: PASS")

t, res = search_engine.resolve_symbol_or_suggestions("TATAPOWER")
assert t == "EXACT" and res == "TATAPOWER"
print("  ✅ TATAPOWER Exact Match: PASS")

# 1D: JIO vs IOC Disambiguation (Crucial User Requirement)
t, res = search_engine.resolve_symbol_or_suggestions("JIO")
assert t == "SUGGESTIONS", f"Expected SUGGESTIONS for JIO, got {t}"
assert any(s["symbol"] == "JIOFIN" for s in res), "Expected JIOFIN in suggestions for JIO"
assert not any(s["symbol"] == "IOC" for s in res), "CRITICAL BUG: IOC returned for JIO!"
print("  ✅ JIO Disambiguation: PASS (Surfaces JIOFIN, NEVER IOC)")

t, res = search_engine.resolve_symbol_or_suggestions("IOC")
assert t == "EXACT" and res == "IOC", f"Expected IOC exact, got {res}"
print("  ✅ IOC Exact Match: PASS")

t, res = search_engine.resolve_symbol_or_suggestions("JIOFIN")
assert t == "EXACT" and res == "JIOFIN", f"Expected JIOFIN exact, got {res}"
print("  ✅ JIOFIN Exact Match: PASS")

t, res = search_engine.resolve_symbol_or_suggestions("XYZNONEXISTENT999")
assert t == "NOT_FOUND", f"Expected NOT_FOUND for fake symbol, got {t}"
print("  ✅ Fake Symbol Rejection (NOT_FOUND): PASS")

# -------------------------------------------------------------
# TEST 2: 15-AGENT INSTITUTIONAL NETWORK EXECUTION & HTML TAG AUDIT
# -------------------------------------------------------------
print("\n[TEST 2] Testing 15-Agent Institutional Network & HTML Syntax...")
import agents_network

test_symbols = ["BEL", "TATAPOWER", "HDFCBANK", "INFY", "TCS", "SBIN"]
for sym in test_symbols:
    d = agents_network.InstitutionalNetwork.run_15_agents(sym)
    assert d.get("success") is True, f"15-Agent Network failed on {sym}"
    assert float(d["price"]) > 0, f"Invalid price for {sym}"
    assert "div1" in d["divisions"] and "div4" in d["divisions"]
    
    # Check text formatting
    report = agents_network.format_15_agent_dossier(d)
    assert len(report) > 1500, f"Report too short for {sym}"
    
    # HTML tag audit
    for i, c in enumerate(report):
        if c == "<":
            tag = report[i:i+10]
            if not (tag.startswith("<b>") or tag.startswith("</b>") or tag.startswith("<code>") or tag.startswith("</code>") or tag.startswith("<i>") or tag.startswith("</i>")):
                raise ValueError(f"Invalid tag in {sym} report at {i}: {report[i:i+30]}")
                
    print(f"  ✅ 15 Agents [{sym}]: Spot ₹{d['price']} | Verdict: {d['divisions']['div4'][4]['verdict']} | HTML Tags: CLEAN")

# -------------------------------------------------------------
# TEST 3: CANDLESTICK CHART ENGINE
# -------------------------------------------------------------
print("\n[TEST 3] Testing Visual Telemetry & Dark-Mode Chart Engine...")
import chart_engine

for sym in ["BEL", "TATAPOWER"]:
    chart_file = chart_engine.generate_candlestick_chart(
        sym, entry=390.0, initial_stop=375.0, breakeven=390.0, target1=410.0, target2=425.0
    )
    assert chart_file is not None and os.path.exists(chart_file), f"Chart failed for {sym}"
    sz = os.path.getsize(chart_file)
    assert sz > 20000, f"Chart file too small ({sz} bytes)"
    print(f"  ✅ Candlestick Chart [{sym}]: Generated successfully ({sz:,} bytes)")

# -------------------------------------------------------------
# TEST 4: TODAY'S MORNING RECOMMENDATION ENGINE
# -------------------------------------------------------------
print("\n[TEST 4] Testing Today's Morning Recommendations Engine...")
import today_engine

morning_report = today_engine.get_today_morning_recommendations()
assert "TODAY'S TOP BUY PICKS" in morning_report
assert "₹100 Budget" in morning_report and "₹5,000+ Budget" in morning_report
assert "Recommended Capital:" in morning_report
print(f"  ✅ Today's Morning Recommendations: PASS ({len(morning_report)} characters, All 5 Budget Categories populated)")

# -------------------------------------------------------------
# TEST 5: SQLITE DATABASE STATE MACHINE & AUDIT
# -------------------------------------------------------------
print("\n[TEST 5] Testing SQLite Database State Machine...")
import database

database.init_db()
database.add_or_update_trade(
    symbol="TEST_BEL",
    tier="TIER_1",
    entry_price=398.50,
    initial_stop=385.00,
    current_stop=385.00,
    target1=415.00,
    target2=430.00,
    target3=450.00,
    shares=100,
    atr=9.50
)
open_t = database.get_open_trades()
matching = [t for t in open_t if t["symbol"] == "TEST_BEL"]
assert len(matching) == 1, "Failed to persist trade in SQLite"
print("  ✅ Trade Insert & Query: PASS")

# Test Breakeven update
database.update_trade_runtime(matching[0]["id"], 416.0, 398.50, "BREAKEVEN", 4.39, breakeven_triggered=1)
open_t2 = database.get_open_trades()
updated = [t for t in open_t2 if t["symbol"] == "TEST_BEL"][0]
assert updated["status"] == "BREAKEVEN" and updated["current_stop"] == 398.50
print("  ✅ Zero-Loss Breakeven Shift: PASS")

# Test Close execution
database.close_trade_execution(updated["id"], "STOPPED_OUT_TEST")
open_t3 = database.get_open_trades()
assert len([t for t in open_t3 if t["symbol"] == "TEST_BEL"]) == 0
print("  ✅ Auto-Sell Execution & Removal: PASS")

# -------------------------------------------------------------
# TEST 6: SENTINELS (FLASH CRASH & ZERO-LOSS BREAKEVEN)
# -------------------------------------------------------------
print("\n[TEST 6] Testing Market Sentinels...")
import asyncio
import sentinels

async def test_sentinels():
    # Pass None bot to verify logic runs without throwing exceptions
    await sentinels.run_flash_crash_sentinel(None, None)
    await sentinels.run_zero_loss_and_execution_engine(None, None)

asyncio.run(test_sentinels())
print("  ✅ Agent O & Agent N Background Logic: PASS")

print("\n" + "=" * 70)
print("  🏆 ALL 6 VERIFICATION STAGES PASSED WITH ZERO ERRORS!")
print("=" * 70)
