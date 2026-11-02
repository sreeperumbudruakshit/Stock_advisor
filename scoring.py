"""
Signal scoring logic - implements exact weights and criteria
"""

from config import WEIGHTS

def score_trend(price, ma_50, ma_200):
    """Score trend signal (max 15 points)"""
    if price > ma_50 and price > ma_200:
        return 15  # Clear uptrend
    elif price > ma_50:
        return 10  # Uptrend forming
    elif ma_50 < price < ma_200 or ma_200 < price < ma_50:
        return 5   # Sideways
    else:
        return 0   # Downtrend

def score_macd(macd_line, macd_signal, histogram, prev_histogram):
    """Score MACD signal (max 15 points)"""
    bullish_cross = macd_line > macd_signal and prev_histogram < 0 < histogram
    histogram_expanding = histogram > prev_histogram
    
    if bullish_cross and histogram > 0 and histogram_expanding:
        return 15  # Bullish crossover + expanding
    elif bullish_cross and histogram > 0:
        return 10  # Bullish crossover, positive but flat
    elif macd_line > macd_signal:
        return 5   # MACD above signal but no recent cross
    else:
        return 0   # Bearish

def score_rsi(rsi):
    """Score RSI signal (max 12 points) - REFINED FOR SWING TRADING"""
    if 30 <= rsi <= 50:
        return 12  # Optimal entry zone
    elif 50 < rsi <= 65:
        return 8   # Moderate strength
    elif 20 <= rsi < 30:
        return 6   # Extreme oversold
    elif 65 < rsi <= 70:
        return 4   # Extended
    elif rsi > 70 or rsi < 20:
        return 0   # Overbought or capitulation
    else:
        return 0

def score_volume(volume_ratio):
    """Score volume signal (max 10 points)"""
    if volume_ratio >= 1.5:
        return 10  # Strong volume
    elif volume_ratio >= 1.2:
        return 6   # Above average
    elif volume_ratio >= 0.9:
        return 3   # Near average
    else:
        return 0   # Below average

def score_moving_averages(ma_50, ma_200):
    """Score MA relationship (max 8 points)"""
    if ma_50 > ma_200:
        return 8   # Golden cross setup
    elif ma_50 > ma_200 * 0.98:  # Within 2%
        return 5   # Approaching from below
    elif abs(ma_50 - ma_200) / ma_200 < 0.02:
        return 2   # MAs flat or mixed
    else:
        return 0   # Death cross

def score_eps_growth(eps_growth):
    """Score EPS growth (max 8 points)"""
    if eps_growth > 15:
        return 8
    elif eps_growth > 5:
        return 5
    elif eps_growth > 0:
        return 2
    else:
        return 0

def score_sales_growth(sales_growth):
    """Score sales growth (max 7 points)"""
    if sales_growth > 10:
        return 7
    elif sales_growth > 5:
        return 4
    elif sales_growth > 0:
        return 2
    else:
        return 0

def score_pe_ratio(pe_ratio):
    """Score PE ratio (max 5 points)"""
    if pe_ratio <= 0:
        return 0  # Loss-making
    elif 15 <= pe_ratio <= 25:
        return 5  # Reasonable
    elif (10 <= pe_ratio < 15) or (25 < pe_ratio <= 35):
        return 3  # Acceptable
    elif pe_ratio < 10 or (35 < pe_ratio <= 50):
        return 1  # Value trap or expensive
    else:
        return 0  # Bubble

def score_debt(debt_to_equity):
    """Score debt levels (max 5 points)"""
    if debt_to_equity < 0.5:
        return 5  # Low debt
    elif debt_to_equity < 1.0:
        return 3  # Moderate
    elif debt_to_equity < 2.0:
        return 1  # High debt
    else:
        return 0  # Overleveraged

def score_chart_pattern(pattern):
    """Score chart pattern (max 4 points)"""
    if pattern == 'bullish':
        return 4
    elif pattern == 'neutral':
        return 2
    else:
        return 0

def score_bollinger_bands(price, bb_upper, bb_middle, bb_lower, trend_score):
    """Score Bollinger Bands (max 3 points)"""
    if price <= bb_lower * 1.02 and trend_score >= 10:  # Near lower band in uptrend
        return 3
    elif bb_lower < price < bb_upper:  # In middle
        return 2
    else:  # At upper band
        return 0

def score_profit_margin(profit_margin, has_trend_data=False):
    """Score profit margin trends (max 3 points)"""
    # Simplified - in production, compare QoQ
    if profit_margin > 15:
        return 3  # High margins
    elif profit_margin > 10:
        return 1  # Stable margins
    else:
        return 0  # Low margins

def score_cash_flow(cash_flow_positive, fcf_positive):
    """Score cash flow (max 2 points)"""
    if cash_flow_positive and fcf_positive:
        return 2  # Strong cash flow
    elif cash_flow_positive:
        return 1  # Positive OCF
    else:
        return 0  # Negative

def score_revenue_quality(eps_growth, sales_growth):
    """Score revenue quality (max 2 points)"""
    # Simplified - checks if growth is sustainable
    if sales_growth > 0 and eps_growth > 0 and abs(eps_growth - sales_growth) < 20:
        return 2  # Diversified, quality revenue
    elif sales_growth > 0:
        return 1  # Growing but check needed
    else:
        return 0  # Concerning

def score_ownership_changes():
    """Score FII/Promoter changes (max 1 point)"""
    # Placeholder - requires additional data source
    return 0  # Neutral unless data available

def calculate_technical_score(indicators, pattern):
    """Calculate total technical score (max 60 points)"""
    trend_score = score_trend(indicators['price'], indicators['ma_50'], indicators['ma_200'])
    macd_score = score_macd(
        indicators['macd_line'], 
        indicators['macd_signal'], 
        indicators['macd_histogram'],
        indicators['macd_prev_histogram']
    )
    rsi_score = score_rsi(indicators['rsi'])
    volume_score = score_volume(indicators['volume_ratio'])
    ma_score = score_moving_averages(indicators['ma_50'], indicators['ma_200'])
    
    technical_score = trend_score + macd_score + rsi_score + volume_score + ma_score
    
    breakdown = {
        'trend': trend_score,
        'macd': macd_score,
        'rsi': rsi_score,
        'volume': volume_score,
        'ma': ma_score,
        'total': technical_score
    }
    
    return technical_score, breakdown

def calculate_fundamental_score(fundamentals):
    """Calculate total fundamental score (max 25 points)"""
    if not fundamentals:
        return 0, {}
    
    eps_score = score_eps_growth(fundamentals['eps_growth'])
    sales_score = score_sales_growth(fundamentals['sales_growth'])
    pe_score = score_pe_ratio(fundamentals['pe_ratio'])
    debt_score = score_debt(fundamentals['debt_to_equity'])
    
    fundamental_score = eps_score + sales_score + pe_score + debt_score
    
    breakdown = {
        'eps_growth': eps_score,
        'sales_growth': sales_score,
        'pe_ratio': pe_score,
        'debt': debt_score,
        'total': fundamental_score
    }
    
    return fundamental_score, breakdown

def calculate_supporting_score(indicators, pattern, fundamentals):
    """Calculate total supporting score (max 15 points)"""
    pattern_score = score_chart_pattern(pattern)
    bb_score = score_bollinger_bands(
        indicators['price'], 
        indicators['bb_upper'], 
        indicators['bb_middle'], 
        indicators['bb_lower'],
        score_trend(indicators['price'], indicators['ma_50'], indicators['ma_200'])
    )
    
    if fundamentals:
        margin_score = score_profit_margin(fundamentals['profit_margin'])
        cf_score = score_cash_flow(fundamentals['cash_flow_positive'], fundamentals['fcf_positive'])
        rev_quality_score = score_revenue_quality(fundamentals['eps_growth'], fundamentals['sales_growth'])
    else:
        margin_score = 0
        cf_score = 0
        rev_quality_score = 0
    
    ownership_score = score_ownership_changes()
    
    supporting_score = pattern_score + bb_score + margin_score + cf_score + rev_quality_score + ownership_score
    
    breakdown = {
        'pattern': pattern_score,
        'bollinger': bb_score,
        'margins': margin_score,
        'cash_flow': cf_score,
        'revenue_quality': rev_quality_score,
        'ownership': ownership_score,
        'total': supporting_score
    }
    
    return supporting_score, breakdown