"""
Technical indicator calculations
"""

import pandas as pd
import numpy as np
from config import TECHNICAL_PARAMS

def calculate_rsi(data, period=14):
    """Calculate RSI"""
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    
    return rsi

def calculate_macd(data, fast=12, slow=26, signal=9):
    """Calculate MACD"""
    ema_fast = data['Close'].ewm(span=fast).mean()
    ema_slow = data['Close'].ewm(span=slow).mean()
    
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal).mean()
    histogram = macd_line - signal_line
    
    return macd_line, signal_line, histogram

def calculate_moving_averages(data, short=50, long=200):
    """Calculate moving averages"""
    ma_short = data['Close'].rolling(window=short).mean()
    ma_long = data['Close'].rolling(window=long).mean()
    
    return ma_short, ma_long

def calculate_bollinger_bands(data, period=20, std=2):
    """Calculate Bollinger Bands"""
    sma = data['Close'].rolling(window=period).mean()
    std_dev = data['Close'].rolling(window=period).std()
    
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    
    return upper_band, sma, lower_band

def calculate_volume_metrics(data, period=20):
    """Calculate volume metrics"""
    volume_ma = data['Volume'].rolling(window=period).mean()
    volume_ratio = data['Volume'].iloc[-1] / volume_ma.iloc[-1] if volume_ma.iloc[-1] > 0 else 0
    
    return volume_ma, volume_ratio

def calculate_all_indicators(data):
    """
    Calculate all technical indicators
    
    Args:
        data: DataFrame with OHLCV data
    
    Returns:
        Dictionary with all calculated indicators
    """
    params = TECHNICAL_PARAMS
    
    # Calculate indicators
    rsi = calculate_rsi(data, params['rsi_period'])
    macd_line, signal_line, histogram = calculate_macd(
        data, params['macd_fast'], params['macd_slow'], params['macd_signal']
    )
    ma_short, ma_long = calculate_moving_averages(
        data, params['ma_short'], params['ma_long']
    )
    bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(
        data, params['bb_period'], params['bb_std']
    )
    volume_ma, volume_ratio = calculate_volume_metrics(
        data, params['volume_ma_period']
    )
    
    # Get latest values
    indicators = {
        'rsi': rsi.iloc[-1],
        'macd_line': macd_line.iloc[-1],
        'macd_signal': signal_line.iloc[-1],
        'macd_histogram': histogram.iloc[-1],
        'macd_prev_histogram': histogram.iloc[-2] if len(histogram) > 1 else 0,
        'ma_50': ma_short.iloc[-1],
        'ma_200': ma_long.iloc[-1],
        'price': data['Close'].iloc[-1],
        'volume': data['Volume'].iloc[-1],
        'volume_ma': volume_ma.iloc[-1],
        'volume_ratio': volume_ratio,
        'bb_upper': bb_upper.iloc[-1],
        'bb_middle': bb_middle.iloc[-1],
        'bb_lower': bb_lower.iloc[-1],
        
        # For charting
        'rsi_series': rsi,
        'macd_series': macd_line,
        'signal_series': signal_line,
        'histogram_series': histogram,
        'ma_50_series': ma_short,
        'ma_200_series': ma_long,
        'bb_upper_series': bb_upper,
        'bb_middle_series': bb_middle,
        'bb_lower_series': bb_lower
    }
    
    return indicators

def detect_chart_pattern(data):
    """
    Simple chart pattern detection
    
    Returns:
        String: 'bullish', 'bearish', 'neutral'
    """
    # Simplified pattern detection
    # Check last 20 bars for basic patterns
    
    if len(data) < 20:
        return 'neutral'
    
    recent = data.tail(20)
    
    # Simple trend detection
    first_third = recent.head(7)['Close'].mean()
    last_third = recent.tail(7)['Close'].mean()
    
    change_pct = ((last_third / first_third) - 1) * 100
    
    if change_pct > 3:
        return 'bullish'
    elif change_pct < -3:
        return 'bearish'
    else:
        return 'neutral'

def detect_support_resistance(data, lookback=50):
    """
    Detect key support and resistance levels
    
    Returns:
        Dictionary with support and resistance levels
    """
    if len(data) < lookback:
        lookback = len(data)
    
    recent = data.tail(lookback)
    
    # Find local maxima and minima
    resistance = recent['High'].max()
    support = recent['Low'].min()
    
    current_price = data['Close'].iloc[-1]
    
    return {
        'resistance': resistance,
        'support': support,
        'current_price': current_price,
        'distance_to_resistance': ((resistance / current_price) - 1) * 100,
        'distance_to_support': ((current_price / support) - 1) * 100
    }