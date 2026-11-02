"""
Core decision engine - implements exact decision logic
"""

from config import THRESHOLDS, CONFIDENCE_ADJUSTMENTS, POSITION_SIZING
from scoring import calculate_technical_score, calculate_fundamental_score, calculate_supporting_score

def calculate_market_penalty(market_context):
    """Calculate market context confidence penalty"""
    if not market_context:
        return 0
    
    penalty = 0
    breadth = market_context.get('market_breadth', 50)
    nifty_change = market_context.get('nifty_5d_change', 0)
    
    # Market breadth penalties
    if breadth > 60:
        penalty += 0
    elif 40 <= breadth <= 60:
        penalty += 10
    elif 30 <= breadth < 40:
        penalty += 20
    else:  # < 30
        penalty += 35
    
    # NIFTY trend penalties
    if nifty_change > 2:
        penalty += 0
    elif -2 <= nifty_change <= 2:
        penalty += 5
    else:  # < -5
        penalty += 25
    
    # Cap at maximum
    penalty = min(penalty, CONFIDENCE_ADJUSTMENTS['max_market_penalty'])
    
    return penalty

def calculate_confidence(base_score, fundamental_score, volume_score, market_context):
    """
    Calculate final confidence with simplified adjustments (max 3)
    """
    # Step 1: Base confidence
    confidence = (base_score / 100) * 100
    
    # Step 2: Apply maximum 3 adjustments
    
    # Adjustment 1: Weak fundamentals
    if fundamental_score < 10:
        confidence = confidence * CONFIDENCE_ADJUSTMENTS['weak_fundamentals_multiplier']
    
    # Adjustment 2: Market context penalty
    market_penalty = calculate_market_penalty(market_context)
    confidence = confidence - market_penalty
    
    # Adjustment 3: Low volume
    if volume_score == 0:
        confidence = confidence * CONFIDENCE_ADJUSTMENTS['low_volume_multiplier']
    
    # Step 3: Apply caps
    confidence = max(confidence, CONFIDENCE_ADJUSTMENTS['min_confidence'])
    confidence = min(confidence, CONFIDENCE_ADJUSTMENTS['max_confidence'])
    
    return round(confidence, 1)

def determine_decision(base_score):
    """Determine buy decision based on score"""
    if base_score >= THRESHOLDS['strong_buy']:
        return 'STRONG BUY'
    elif base_score >= THRESHOLDS['buy']:
        return 'BUY'
    elif base_score >= THRESHOLDS['hold']:
        return 'BUY'  # Medium confidence
    elif base_score >= THRESHOLDS['no_buy']:
        return 'NO BUY / HOLD'
    else:
        return 'NO BUY'

def calculate_position_size(base_score, final_confidence):
    """Calculate position size as % of standard allocation"""
    if base_score >= 85:
        base_size = POSITION_SIZING['score_85_plus']
    elif base_score >= 70:
        base_size = POSITION_SIZING['score_70_84']
    elif base_score >= 55:
        base_size = POSITION_SIZING['score_55_69']
    else:
        return 0
    
    # Adjust based on confidence
    if final_confidence >= 70:
        multiplier = POSITION_SIZING['confidence_70_plus']
    elif final_confidence >= 55:
        multiplier = POSITION_SIZING['confidence_55_69']
    elif final_confidence >= 40:
        multiplier = POSITION_SIZING['confidence_40_54']
    else:
        multiplier = POSITION_SIZING['confidence_below_40']
    
    position_size = base_size * multiplier
    return round(position_size, 0)

def generate_reasoning(tech_breakdown, fund_breakdown, supp_breakdown, decision, confidence):
    """Generate human-readable reasoning"""
    strengths = []
    concerns = []
    
    # Technical strengths
    if tech_breakdown['trend'] >= 10:
        strengths.append("Strong trend structure with price sustaining above key moving averages, supporting directional continuation.")
    if tech_breakdown['macd'] >= 10:
        strengths.append("Bullish momentum confirmed as MACD supports upside continuation in the near term.")
    if tech_breakdown['rsi'] >= 10:
        strengths.append(f"RSI is in a constructive zone ({tech_breakdown.get('rsi_value', 'favorable')}), indicating balanced upside potential.")
    if tech_breakdown['volume'] >= 6:
        strengths.append(f"Volume participation is healthy ({tech_breakdown.get('volume_ratio', '>')}x average), improving move reliability.")
    
    # Technical concerns
    if tech_breakdown['rsi'] == 0:
        concerns.append("RSI is at an extreme level, which can increase reversal risk and reduce reward quality.")
    if tech_breakdown['volume'] == 0:
        concerns.append("Volume is below ideal levels, suggesting weaker conviction behind the current price action.")
    if tech_breakdown['macd'] == 0:
        concerns.append("MACD remains below signal support, indicating weak short-term momentum confirmation.")
    
    # Fundamental strengths
    if fund_breakdown['total'] >= 20:
        strengths.append("Fundamental quality is strong with supportive growth metrics backing technical setup strength.")
    if fund_breakdown['debt'] >= 3:
        strengths.append("Balance-sheet leverage appears manageable, reducing financial stress risk in volatile phases.")
    
    # Fundamental concerns
    if fund_breakdown['total'] < 10:
        concerns.append("Fundamental score is weak, reflecting limited earnings support and lower quality conviction.")
    if fund_breakdown['debt'] == 0:
        concerns.append("Debt profile is elevated versus preferred levels, which may amplify downside pressure.")
    
    # Limit to top 3 strengths and 2 concerns
    strengths = strengths[:3]
    concerns = concerns[:2]
    
    if not strengths:
        strengths = ["Minimal technical setup identified"]
    if not concerns:
        concerns = ["No major red flags identified"]
    
    return {
        'strengths': strengths,
        'concerns': concerns
    }

def get_score_label(score):
    """Interpret score into readable opportunity zone."""
    if score >= 70:
        return "Strong Buy Zone"
    elif score >= 50:
        return "Moderate Opportunity"
    return "Weak Setup / Avoid"

def generate_decision_summary(decision, score_label, confidence, tech_breakdown, fund_breakdown):
    """Generate concise 2-3 line summary for decision readability."""
    momentum_state = "supported" if tech_breakdown.get('macd', 0) >= 10 else "not fully confirmed"
    fundamentals_state = "strong" if fund_breakdown.get('total', 0) >= 20 else "mixed"
    return (
        f"Decision is {decision} with {confidence}% confidence, and the setup is classified as {score_label}. "
        f"Momentum is {momentum_state} while fundamental backing appears {fundamentals_state}. "
        "Use entry discipline and risk controls before execution."
    )

def evaluate_stock(price_data, fundamentals, market_context):
    """
    Main evaluation function - orchestrates entire decision process
    
    Returns complete analysis dictionary
    """
    from indicators import calculate_all_indicators, detect_chart_pattern
    from fundamentals import process_fundamentals
    
    # Calculate all indicators
    indicators = calculate_all_indicators(price_data)
    pattern = detect_chart_pattern(price_data)
    processed_fundamentals = process_fundamentals(fundamentals)
    
    # Calculate scores
    tech_score, tech_breakdown = calculate_technical_score(indicators, pattern)
    fund_score, fund_breakdown = calculate_fundamental_score(processed_fundamentals)
    supp_score, supp_breakdown = calculate_supporting_score(indicators, pattern, processed_fundamentals)
    
    # Base score
    base_score = tech_score + fund_score + supp_score
    
    # Confidence
    volume_score = tech_breakdown['volume']
    final_confidence = calculate_confidence(base_score, fund_score, volume_score, market_context)
    
    # Decision
    decision = determine_decision(base_score)
    
    # Position size
    position_size = calculate_position_size(base_score, final_confidence)
    
    # Reasoning
    reasoning = generate_reasoning(tech_breakdown, fund_breakdown, supp_breakdown, decision, final_confidence)
    
    # Actionable output fields (fallback-safe, never NaN)
    close_series = price_data['Close'] if 'Close' in price_data.columns else None
    low_series = price_data['Low'] if 'Low' in price_data.columns else None

    raw_price_now = close_series.iloc[-1] if close_series is not None and len(close_series) > 0 else 0.0
    raw_entry_price = raw_price_now

    raw_stop_loss = raw_entry_price * 0.95
    raw_target_min = raw_entry_price * 1.05
    raw_target_max = raw_entry_price * 1.10

    risk = raw_entry_price - raw_stop_loss
    reward = raw_target_min - raw_entry_price
    raw_risk_reward = (reward / risk) if risk > 0 else 0

    def safe_number(value, fallback):
        """Return numeric fallback-safe value, rounded to 2 decimals."""
        try:
            numeric = float(value)
            if numeric != numeric:  # NaN check
                numeric = float(fallback)
        except (TypeError, ValueError):
            numeric = float(fallback)
        return round(numeric, 2)

    price_now = safe_number(raw_price_now, 0.0)
    entry_price = safe_number(raw_entry_price, price_now)
    if entry_price != price_now:
        entry_price = price_now
    stop_loss = safe_number(raw_stop_loss, entry_price * 0.95)
    target_min = safe_number(raw_target_min, entry_price * 1.05)
    target_max = safe_number(raw_target_max, entry_price * 1.10)
    risk_reward = safe_number(raw_risk_reward, 0.0)
    score_label = get_score_label(base_score)
    decision_summary = generate_decision_summary(decision, score_label, final_confidence, tech_breakdown, fund_breakdown)

    # Compile result
    result = {
        'decision': decision,
        'confidence': final_confidence,
        'base_score': base_score,
        'score': base_score,
        'price_now': price_now,
        'entry_price': entry_price,
        'stop_loss': stop_loss,
        'target_min': target_min,
        'target_max': target_max,
        'risk_reward': risk_reward,
        'score_label': score_label,
        'decision_summary': decision_summary,
        'breakdown': {
            'technical': tech_breakdown,
            'fundamental': fund_breakdown,
            'supporting': supp_breakdown
        },
        'position_size': position_size,
        'reasoning': reasoning,
        'reason': {
            'strengths': reasoning['strengths'],
            'risks': reasoning['concerns']
        },
        'indicators': indicators,
        'fundamentals': processed_fundamentals,
        'market_context': market_context
    }
    
    return result

