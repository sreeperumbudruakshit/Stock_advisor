"""
Risk management and execution guidance
"""

import numpy as np
import pandas as pd

def calculate_atr(data, period=14):
    """Calculate Average True Range"""
    high = data['High']
    low = data['Low']
    close = data['Close']
    
    tr1 = high - low
    tr2 = abs(high - close.shift())
    tr3 = abs(low - close.shift())
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    return atr.iloc[-1]

def calculate_stop_loss(price, support, atr):
    """Calculate stop-loss level"""
    # Use tighter of: 2x ATR or below support
    atr_stop = price - (2 * atr)
    support_stop = support * 0.98  # 2% below support
    
    stop_loss = max(atr_stop, support_stop)
    risk_percent = ((price - stop_loss) / price) * 100
    
    return {
        'stop_loss': round(stop_loss, 2),
        'risk_percent': round(risk_percent, 2)
    }

def calculate_targets(price, resistance, expected_return_range):
    """Calculate price targets"""
    # Target 1: Conservative (resistance or 5-8%)
    target_1_resistance = resistance
    target_1_percent = price * 1.06  # 6%
    target_1 = min(target_1_resistance, target_1_percent)
    
    # Target 2: Moderate (8-12%)
    target_2 = price * 1.10  # 10%
    
    return {
        'target_1': round(target_1, 2),
        'target_1_gain': round(((target_1 / price) - 1) * 100, 1),
        'target_2': round(target_2, 2),
        'target_2_gain': round(((target_2 / price) - 1) * 100, 1)
    }

def determine_time_horizon(base_score, confidence):
    """Determine expected holding period"""
    if base_score >= 80 and confidence >= 70:
        return "2-4 weeks (swing trade)"
    elif base_score >= 60:
        return "1-3 weeks (short-term swing)"
    else:
        return "Monitor closely (1-2 weeks)"

def assess_risk_level(risk_percent, confidence, fund_score):
    """Assess overall risk level"""
    risk_score = 0
    
    # Risk from stop-loss distance
    if risk_percent > 7:
        risk_score += 2
    elif risk_percent > 5:
        risk_score += 1
    
    # Risk from confidence
    if confidence < 50:
        risk_score += 2
    elif confidence < 65:
        risk_score += 1
    
    # Risk from fundamentals
    if fund_score < 10:
        risk_score += 1
    
    if risk_score >= 4:
        return "High"
    elif risk_score >= 2:
        return "Medium"
    else:
        return "Low"

def generate_execution_plan(analysis_result, price_data):
    """Generate complete execution guidance"""
    from indicators import detect_support_resistance
    
    price = analysis_result['indicators']['price']
    levels = detect_support_resistance(price_data)
    
    atr = calculate_atr(price_data)
    
    # Stop-loss
    stop_info = calculate_stop_loss(price, levels['support'], atr)
    
    # Targets
    targets = calculate_targets(price, levels['resistance'], (8, 12))
    
    # Time horizon
    time_horizon = determine_time_horizon(
        analysis_result['base_score'],
        analysis_result['confidence']
    )
    
    # Risk level
    risk_level = assess_risk_level(
        stop_info['risk_percent'],
        analysis_result['confidence'],
        analysis_result['breakdown']['fundamental']['total']
    )
    
    # Entry strategy
    if levels['distance_to_support'] < 3:
        entry_type = "Immediate entry near support"
    else:
        entry_type = "Wait for pullback to support"
    
    execution = {
        'entry_price': round(price, 2),
        'entry_range_low': round(levels['support'] * 1.01, 2),
        'entry_range_high': round(price, 2),
        'entry_type': entry_type,
        'stop_loss': stop_info['stop_loss'],
        'risk_percent': stop_info['risk_percent'],
        'target_1': targets['target_1'],
        'target_1_gain': targets['target_1_gain'],
        'target_2': targets['target_2'],
        'target_2_gain': targets['target_2_gain'],
        'time_horizon': time_horizon,
        'risk_level': risk_level,
        'position_size': analysis_result['position_size'],
        'support_level': round(levels['support'], 2),
        'resistance_level': round(levels['resistance'], 2)
    }
    
    return execution