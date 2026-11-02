"""
Logging and tracking system
"""

import pandas as pd
from datetime import datetime
import json
import os

class AnalysisLogger:
    def __init__(self, log_file='analysis_log.csv'):
        self.log_file = log_file
        self.ensure_log_exists()
    
    def ensure_log_exists(self):
        """Create log file if it doesn't exist"""
        if not os.path.exists(self.log_file):
            columns = [
                'timestamp', 'symbol', 'decision', 'confidence', 'base_score',
                'technical_score', 'fundamental_score', 'supporting_score',
                'entry_price', 'stop_loss', 'target_1', 'target_2',
                'position_size', 'risk_level', 'market_breadth', 'notes'
            ]
            df = pd.DataFrame(columns=columns)
            df.to_csv(self.log_file, index=False)
    
    def log_analysis(self, symbol, analysis_result, execution_plan):
        """Log analysis result"""
        log_entry = {
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'symbol': symbol,
            'decision': analysis_result['decision'],
            'confidence': analysis_result['confidence'],
            'base_score': analysis_result['base_score'],
            'technical_score': analysis_result['breakdown']['technical']['total'],
            'fundamental_score': analysis_result['breakdown']['fundamental']['total'],
            'supporting_score': analysis_result['breakdown']['supporting']['total'],
            'entry_price': execution_plan['entry_price'],
            'stop_loss': execution_plan['stop_loss'],
            'target_1': execution_plan['target_1'],
            'target_2': execution_plan['target_2'],
            'position_size': analysis_result['position_size'],
            'risk_level': execution_plan['risk_level'],
            'market_breadth': analysis_result['market_context'].get('market_breadth', 'N/A') if analysis_result['market_context'] else 'N/A',
            'notes': ''
        }
        
        df = pd.read_csv(self.log_file)
        df = pd.concat([df, pd.DataFrame([log_entry])], ignore_index=True)
        df.to_csv(self.log_file, index=False)
    
    def get_history(self, limit=50):
        """Get recent analysis history"""
        if os.path.exists(self.log_file):
            df = pd.read_csv(self.log_file)
            return df.tail(limit)
        return pd.DataFrame()
    
    def get_symbol_history(self, symbol):
        """Get history for specific symbol"""
        if os.path.exists(self.log_file):
            df = pd.read_csv(self.log_file)
            return df[df['symbol'] == symbol]
        return pd.DataFrame()