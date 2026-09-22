import datetime
import agents_network

def get_today_morning_recommendations():
    """
    Pre-Market Daily Dispatch (09:08 AM IST):
    Runs 15-agent consensus across all 5 price brackets and returns
    standardized Rapid Intel Cards.
    """
    now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M IST")
    cards = []

    active_tiers = ["TIER_100", "TIER_200", "TIER_500", "TIER_1000", "TIER_2000", "TIER_5000"]
    for tier_key in active_tiers:
        t_info = agents_network.PRICE_TIERS[tier_key]
        candidates = t_info["universe"]
        best_candidate = None
        for sym in candidates[:3]:
            analysis = agents_network.InstitutionalNetwork.run_15_agents(sym)
            if analysis.get("success"):
                if best_candidate is None or analysis["consensus_score"] > best_candidate["consensus_score"]:
                    best_candidate = analysis
        if best_candidate:
            card = agents_network.format_rapid_intel_card(best_candidate)
            cards.append(card)

    combined_body = "\n\n".join(cards)
    header = f"""🌅 <b>TODAY'S TOP BUY PICKS (SIMPLE TRADING GUIDE)</b>
<i>Updated: {now_str} | Market Opens 09:15 AM | Principle: Safety First</i>
================================================================
<b>Recommended Budget Categories:</b>
• <b>Under ₹100 Budget:</b> ₹100 and below (≤ ₹100)
• <b>₹200 – ₹499 Budget:</b> ₹200 to ₹499
• <b>₹500 – ₹999 Budget:</b> ₹500 to ₹999
• <b>₹1,000 – ₹1,999 Budget:</b> ₹1,000 to ₹1,999
• <b>₹2,000 – ₹4,999 Budget:</b> ₹2,000 to ₹4,999
• <b>₹5,000+ Budget:</b> ₹5,000 and above
<b>Recommended Capital:</b> Risk is strictly capped at maximum ₹500 per stock across all budget categories.
================================================================\n\n"""
    
    return header + combined_body

