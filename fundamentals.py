"""
Fundamental analysis processing
"""

def _safe_number(value, default=0.0):
    """Convert value to float safely, returning default for invalid inputs."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

def process_fundamentals(fundamental_data):
    """
    Process raw fundamental data into usable metrics
    
    Args:
        fundamental_data: Dictionary from data_fetch
    
    Returns:
        Dictionary with processed fundamental metrics
    """
    if not fundamental_data:
        return None
    
    # Extract and process metrics
    earnings_growth = _safe_number(fundamental_data.get('earnings_growth'), 0)
    revenue_growth = _safe_number(fundamental_data.get('revenue_growth'), 0)
    pe_ratio = _safe_number(fundamental_data.get('pe_ratio'), 0)
    debt_to_equity_raw = _safe_number(fundamental_data.get('debt_to_equity'), 0)
    profit_margins = _safe_number(fundamental_data.get('profit_margins'), 0)
    operating_cash_flow = _safe_number(fundamental_data.get('operating_cash_flow'), 0)
    free_cash_flow = _safe_number(fundamental_data.get('free_cash_flow'), 0)

    processed = {
        'eps_growth': earnings_growth * 100,
        'sales_growth': revenue_growth * 100,
        'pe_ratio': pe_ratio,
        'debt_to_equity': debt_to_equity_raw / 100,
        'profit_margin': profit_margins * 100,
        'operating_cash_flow': operating_cash_flow,
        'free_cash_flow': free_cash_flow,
        'sector': fundamental_data.get('sector', 'Unknown')
    }
    
    # Calculate derived metrics
    processed['cash_flow_positive'] = processed['operating_cash_flow'] > 0
    processed['fcf_positive'] = processed['free_cash_flow'] > 0
    
    return processed

def get_fundamental_quality_assessment(processed_fundamentals):
    """
    Assess overall fundamental quality
    
    Returns:
        String: 'strong', 'moderate', 'weak'
    """
    if not processed_fundamentals:
        return 'weak'
    
    score = 0
    
    # EPS growth
    if processed_fundamentals['eps_growth'] > 15:
        score += 2
    elif processed_fundamentals['eps_growth'] > 5:
        score += 1
    
    # Sales growth
    if processed_fundamentals['sales_growth'] > 10:
        score += 2
    elif processed_fundamentals['sales_growth'] > 5:
        score += 1
    
    # PE ratio
    if 15 <= processed_fundamentals['pe_ratio'] <= 25:
        score += 2
    elif 10 <= processed_fundamentals['pe_ratio'] < 35:
        score += 1
    
    # Debt
    if processed_fundamentals['debt_to_equity'] < 0.5:
        score += 2
    elif processed_fundamentals['debt_to_equity'] < 1.0:
        score += 1
    
    if score >= 6:
        return 'strong'
    elif score >= 3:
        return 'moderate'
    else:
        return 'weak'