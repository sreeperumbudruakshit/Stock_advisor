"""
Paper trading simulation module
"""

import pandas as pd
from datetime import datetime

class PaperTradingPortfolio:
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.available_capital = initial_capital
        self.positions = []
        self.trade_history = []
    
    def execute_trade(self, symbol, entry_price, position_size_percent, stop_loss):
        """Execute a paper trade"""
        try:
            entry_price = float(entry_price)
            position_size_percent = float(position_size_percent)
            stop_loss = float(stop_loss)
        except (TypeError, ValueError):
            return {"status": "failed", "reason": "Invalid trade inputs"}

        if entry_price <= 0:
            return {"status": "failed", "reason": "Invalid entry price"}

        investment_amount = (self.available_capital * position_size_percent) / 100
        
        if investment_amount > self.available_capital:
            return {"status": "failed", "reason": "Insufficient capital"}
        
        shares = int(investment_amount // entry_price)
        if shares <= 0:
            return {"status": "failed", "reason": "Investment too low for current price"}
        actual_investment = shares * entry_price
        current_value = shares * entry_price
        profit_loss = current_value - actual_investment
        
        position = {
            'symbol': symbol,
            'entry_price': entry_price,
            'shares': shares,
            'quantity': shares,
            'investment': actual_investment,
            'current_value': current_value,
            'profit_loss': profit_loss,
            'stop_loss': stop_loss,
            'entry_date': datetime.now().strftime('%Y-%m-%d'),
            'status': 'open'
        }
        
        self.positions.append(position)
        self.available_capital -= actual_investment
        
        return {"status": "success", "position": position}

    def calculate_trade_metrics(self, investment_amount, price_now, entry_price, target_min, target_max):
        """Calculate paper trading metrics with NaN-safe fallbacks."""
        try:
            investment_amount = float(investment_amount)
            price_now = float(price_now)
            entry_price = float(entry_price)
            target_min = float(target_min)
            target_max = float(target_max)
        except (TypeError, ValueError):
            return None

        if (
            investment_amount <= 0 or
            price_now <= 0 or
            entry_price <= 0 or
            price_now != price_now or
            entry_price != entry_price
        ):
            return None

        quantity = int(investment_amount // price_now)
        total_invested = quantity * price_now
        current_value = quantity * price_now
        profit = current_value - total_invested
        profit_percent = (profit / total_invested) * 100 if total_invested > 0 else 0.0
        target_min_profit = (target_min - entry_price) * quantity
        target_max_profit = (target_max - entry_price) * quantity

        return {
            "investment_amount": round(investment_amount, 2),
            "price_now": round(price_now, 2),
            "quantity": int(quantity),
            "total_invested": round(total_invested, 2),
            "current_value": round(current_value, 2),
            "profit": round(profit, 2),
            "profit_percent": round(profit_percent, 2),
            "target_min_profit": round(target_min_profit, 2),
            "target_max_profit": round(target_max_profit, 2),
        }
    
    def update_position(self, symbol, current_price):
        """Update position with current price"""
        for position in self.positions:
            if position['symbol'] == symbol and position['status'] == 'open':
                position['current_price'] = current_price
                position['current_value'] = position['shares'] * current_price
                position['profit_loss'] = position['current_value'] - position['investment']
                position['profit_loss_percent'] = (position['profit_loss'] / position['investment']) * 100
                
                # Check stop-loss
                if current_price <= position['stop_loss']:
                    position['status'] = 'stopped_out'
                    position['exit_price'] = position['stop_loss']
                    position['exit_date'] = datetime.now().strftime('%Y-%m-%d')
                    self.available_capital += position['shares'] * position['stop_loss']
                    self.trade_history.append(position.copy())
    
    def close_position(self, symbol, exit_price):
        """Manually close a position"""
        for position in self.positions:
            if position['symbol'] == symbol and position['status'] == 'open':
                position['status'] = 'closed'
                position['exit_price'] = exit_price
                position['exit_date'] = datetime.now().strftime('%Y-%m-%d')
                position['current_value'] = position['shares'] * exit_price
                position['profit_loss'] = position['current_value'] - position['investment']
                position['profit_loss_percent'] = (position['profit_loss'] / position['investment']) * 100
                
                self.available_capital += position['current_value']
                self.trade_history.append(position.copy())
    
    def get_portfolio_summary(self):
        """Get current portfolio status"""
        total_invested = sum(p['investment'] for p in self.positions if p['status'] == 'open')
        total_current_value = sum(p.get('current_value', p['investment']) for p in self.positions if p['status'] == 'open')
        unrealized_pl = total_current_value - total_invested
        
        realized_pl = sum(t['profit_loss'] for t in self.trade_history)
        
        total_portfolio_value = self.available_capital + total_current_value
        total_return = ((total_portfolio_value - self.initial_capital) / self.initial_capital) * 100
        
        return {
            'initial_capital': self.initial_capital,
            'available_capital': round(self.available_capital, 2),
            'invested_capital': round(total_invested, 2),
            'current_portfolio_value': round(total_portfolio_value, 2),
            'unrealized_pl': round(unrealized_pl, 2),
            'realized_pl': round(realized_pl, 2),
            'total_return_percent': round(total_return, 2),
            'open_positions': len([p for p in self.positions if p['status'] == 'open']),
            'closed_trades': len(self.trade_history)
        }
    
    def get_open_positions(self):
        """Get list of open positions"""
        return [p for p in self.positions if p['status'] == 'open']
    
    def get_trade_history(self):
        """Get trade history"""
        return self.trade_history

