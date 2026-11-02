"""
Market data retrieval module
"""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta

def _clean_ohlcv(data):
    """Clean OHLCV data and prevent NaN propagation."""
    if data is None or data.empty:
        return None

    required_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
    if not all(col in data.columns for col in required_cols):
        return None

    cleaned = data.copy()
    cleaned = cleaned[required_cols].apply(pd.to_numeric, errors='coerce')
    cleaned = cleaned.dropna(subset=['Open', 'High', 'Low', 'Close'])
    cleaned['Volume'] = cleaned['Volume'].fillna(0)
    cleaned = cleaned[cleaned['Close'] > 0]

    if cleaned.empty:
        return None
    return cleaned

def fetch_stock_data(symbol, period='6mo', interval='1d'):
    """
    Fetch OHLCV data for a stock symbol
    
    Args:
        symbol: Stock ticker (e.g., 'RELIANCE.NS')
        period: Data period ('1mo', '3mo', '6mo', '1y', '2y')
        interval: Data interval ('1d', '1wk', '1mo')
    
    Returns:
        DataFrame with OHLCV data
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period, interval=interval, auto_adjust=False)
        cleaned = _clean_ohlcv(data)
        if cleaned is not None:
            return cleaned

        # Fallback attempt with a slightly larger period for sparse symbols
        fallback_data = ticker.history(period='1y', interval=interval, auto_adjust=False)
        return _clean_ohlcv(fallback_data)
    
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def fetch_fundamental_data(symbol):
    """
    Fetch fundamental data for a stock
    
    Args:
        symbol: Stock ticker
    
    Returns:
        Dictionary with fundamental metrics
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info if ticker.info else {}
        
        # Extract fundamental metrics
        fundamentals = {
            'pe_ratio': info.get('trailingPE', None),
            'debt_to_equity': info.get('debtToEquity', None),
            'profit_margins': info.get('profitMargins', None),
            'revenue_growth': info.get('revenueGrowth', None),
            'earnings_growth': info.get('earningsGrowth', None),
            'operating_cash_flow': info.get('operatingCashflow', None),
            'free_cash_flow': info.get('freeCashflow', None),
            'market_cap': info.get('marketCap', None),
            'sector': info.get('sector', None)
        }
        
        return fundamentals
    
    except Exception as e:
        print(f"Error fetching fundamentals for {symbol}: {e}")
        return None

def fetch_market_context():
    """
    Fetch market breadth and index data
    
    Returns:
        Dictionary with market context metrics
    """
    try:
        # Fetch NIFTY 50 data
        nifty = yf.Ticker('^NSEI')
        nifty_data = nifty.history(period='1mo', auto_adjust=False)
        
        if nifty_data is None or nifty_data.empty or len(nifty_data) < 6 or 'Close' not in nifty_data.columns:
            return None
        nifty_data = nifty_data[['Close']].apply(pd.to_numeric, errors='coerce').dropna()
        if len(nifty_data) < 6:
            return None
        
        # Calculate NIFTY 5-day change
        nifty_5d_change = ((nifty_data['Close'].iloc[-1] / nifty_data['Close'].iloc[-6]) - 1) * 100
        
        # Market breadth (simplified - in production, calculate from constituent stocks)
        # For now, use NIFTY trend as proxy
        if nifty_5d_change > 2:
            breadth = 65  # Strong market
        elif nifty_5d_change > 0:
            breadth = 55  # Moderate market
        elif nifty_5d_change > -2:
            breadth = 45  # Weak market
        else:
            breadth = 25  # Very weak market
        
        market_context = {
            'market_breadth': breadth,
            'nifty_5d_change': nifty_5d_change,
            'nifty_trend': 'uptrend' if nifty_5d_change > 2 else 'neutral' if nifty_5d_change > -2 else 'downtrend'
        }
        
        return market_context
    
    except Exception as e:
        print(f"Error fetching market context: {e}")
        return None

def fetch_batch_stocks(symbols):
    """
    Fetch data for multiple stocks
    
    Args:
        symbols: List of stock tickers
    
    Returns:
        Dictionary {symbol: data_dict}
    """
    results = {}
    
    for symbol in symbols:
        stock_data = fetch_stock_data(symbol)
        fundamental_data = fetch_fundamental_data(symbol)
        
        if stock_data is not None:
            results[symbol] = {
                'price_data': stock_data,
                'fundamentals': fundamental_data
            }
    
    return results

def fetch_latest_price(symbol):
    """
    Fetch latest available price using intraday first, then daily close fallback.

    Returns:
        float or None
    """
    try:
        ticker = yf.Ticker(symbol)

        # Primary: latest intraday 1-minute close
        intraday = ticker.history(period='1d', interval='1m', auto_adjust=False)
        intraday_clean = _clean_ohlcv(intraday)
        if intraday_clean is not None and not intraday_clean.empty:
            return float(intraday_clean['Close'].iloc[-1])

        # Fallback: latest daily close
        daily = ticker.history(period='5d', interval='1d', auto_adjust=False)
        daily_clean = _clean_ohlcv(daily)
        if daily_clean is not None and not daily_clean.empty:
            return float(daily_clean['Close'].iloc[-1])

        return None
    except Exception:
        return None