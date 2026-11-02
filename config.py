"""
System configuration and constants
"""

# SIGNAL WEIGHTS
WEIGHTS = {
    'technical': {
        'trend': 15,
        'macd': 15,
        'rsi': 12,
        'volume': 10,
        'ma': 8
    },
    'fundamental': {
        'eps_growth': 8,
        'sales_growth': 7,
        'pe_ratio': 5,
        'debt': 5
    },
    'supporting': {
        'chart_pattern': 4,
        'bollinger': 3,
        'profit_margin': 3,
        'cash_flow': 2,
        'revenue_quality': 2,
        'ownership': 1
    }
}

# DECISION THRESHOLDS
THRESHOLDS = {
    'strong_buy': 85,
    'buy': 70,
    'hold': 55,
    'no_buy': 40
}

# TECHNICAL PARAMETERS
TECHNICAL_PARAMS = {
    'rsi_period': 14,
    'macd_fast': 12,
    'macd_slow': 26,
    'macd_signal': 9,
    'ma_short': 50,
    'ma_long': 200,
    'bb_period': 20,
    'bb_std': 2,
    'volume_ma_period': 20
}

# CONFIDENCE ADJUSTMENTS
CONFIDENCE_ADJUSTMENTS = {
    'weak_fundamentals_multiplier': 0.85,  # -15%
    'low_volume_multiplier': 0.90,         # -10%
    'market_breadth_penalties': {
        'strong': 0,      # >60%
        'moderate': 10,   # 40-60%
        'weak': 20,       # 30-40%
        'very_weak': 35   # <30%
    },
    'nifty_penalties': {
        'uptrend': 0,     # >+2% in 5 days
        'neutral': 5,     # -2% to +2%
        'downtrend': 25   # <-5% in 5 days
    },
    'max_market_penalty': 40,
    'min_confidence': 25,
    'max_confidence': 95
}

# POSITION SIZING
POSITION_SIZING = {
    'score_85_plus': 100,
    'score_70_84': 80,
    'score_55_69': 60,
    'confidence_70_plus': 1.0,
    'confidence_55_69': 0.85,
    'confidence_40_54': 0.60,
    'confidence_below_40': 0.40
}