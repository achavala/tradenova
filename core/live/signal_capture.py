"""
Signal Capture System
Captures all predictions and signals for analysis and debugging
"""
import logging
import json
from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import pandas as pd

logger = logging.getLogger(__name__)

class SignalCapture:
    """Captures trading signals for analysis"""
    
    def __init__(self, output_dir: str = "./logs/signals"):
        """
        Initialize signal capture
        
        Args:
            output_dir: Directory to save captured signals
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.signals: List[Dict] = []
        self.max_signals = 10000  # Limit memory usage
        
    def capture(
        self,
        symbol: str,
        timestamp: datetime,
        rl_prediction: Optional[Dict] = None,
        multi_agent_signals: Optional[List[Dict]] = None,
        ensemble_signal: Optional[Dict] = None,
        final_decision: Optional[Dict] = None,
        market_data: Optional[Dict] = None
    ):
        """
        Capture a trading signal
        
        Args:
            symbol: Trading symbol
            timestamp: Signal timestamp
            rl_prediction: RL model prediction
            multi_agent_signals: Multi-agent system signals
            ensemble_signal: Ensemble combined signal
            final_decision: Final trading decision
            market_data: Current market data (price, volume, etc.)
        """
        signal = {
            'timestamp': timestamp.isoformat(),
            'symbol': symbol,
            'rl_prediction': rl_prediction,
            'multi_agent_signals': multi_agent_signals,
            'ensemble_signal': ensemble_signal,
            'final_decision': final_decision,
            'market_data': market_data
        }
        
        self.signals.append(signal)
        
        # Limit memory
        if len(self.signals) > self.max_signals:
            self.signals.pop(0)
    
    def save(self, filename: Optional[str] = None):
        """
        Save captured signals to file
        
        Args:
            filename: Output filename (default: signals_YYYYMMDD_HHMMSS.json)
        """
        if not self.signals:
            logger.warning("No signals to save")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"signals_{timestamp}.json"
        
        filepath = self.output_dir / filename
        
        # Convert to JSON-serializable format
        signals_json = []
        for signal in self.signals:
            signals_json.append({
                'timestamp': signal['timestamp'],
                'symbol': signal['symbol'],
                'rl_prediction': self._serialize_dict(signal.get('rl_prediction')),
                'multi_agent_signals': [self._serialize_dict(s) for s in (signal.get('multi_agent_signals') or [])],
                'ensemble_signal': self._serialize_dict(signal.get('ensemble_signal')),
                'final_decision': self._serialize_dict(signal.get('final_decision')),
                'market_data': self._serialize_dict(signal.get('market_data'))
            })
        
        with open(filepath, 'w') as f:
            json.dump(signals_json, f, indent=2)
        
        logger.info(f"Saved {len(self.signals)} signals to {filepath}")
        return filepath
    
    def save_csv(self, filename: Optional[str] = None):
        """
        Save signals as CSV for easy analysis
        
        Args:
            filename: Output filename (default: signals_YYYYMMDD_HHMMSS.csv)
        """
        if not self.signals:
            logger.warning("No signals to save")
            return
        
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"signals_{timestamp}.csv"
        
        filepath = self.output_dir / filename
        
        # Flatten signals for CSV
        rows = []
        for signal in self.signals:
            row = {
                'timestamp': signal['timestamp'],
                'symbol': signal['symbol'],
            }
            
            # RL prediction
            if signal.get('rl_prediction'):
                rl = signal['rl_prediction']
                row['rl_direction'] = rl.get('direction')
                row['rl_confidence'] = rl.get('confidence')
                row['rl_action'] = rl.get('action_value')
            
            # Ensemble
            if signal.get('ensemble_signal'):
                ens = signal['ensemble_signal']
                row['ensemble_direction'] = ens.get('direction')
                row['ensemble_confidence'] = ens.get('confidence')
                row['ensemble_agreement'] = ens.get('agreement')
                row['ensemble_sources'] = ','.join(ens.get('sources', []))
            
            # Final decision
            if signal.get('final_decision'):
                final = signal['final_decision']
                row['final_direction'] = final.get('direction')
                row['final_confidence'] = final.get('confidence')
            
            # Market data
            if signal.get('market_data'):
                md = signal['market_data']
                row['price'] = md.get('price')
                row['volume'] = md.get('volume')
                row['atr'] = md.get('atr')
                row['vix'] = md.get('vix')
            
            rows.append(row)
        
        df = pd.DataFrame(rows)
        df.to_csv(filepath, index=False)
        
        logger.info(f"Saved {len(rows)} signals to CSV: {filepath}")
        return filepath
    
    def _serialize_dict(self, d: Optional[Dict]) -> Optional[Dict]:
        """Convert dict to JSON-serializable format"""
        if d is None:
            return None
        
        serialized = {}
        for k, v in d.items():
            if isinstance(v, (str, int, float, bool, type(None))):
                serialized[k] = v
            elif isinstance(v, (list, tuple)):
                serialized[k] = [self._serialize_dict(item) if isinstance(item, dict) else item for item in v]
            elif isinstance(v, dict):
                serialized[k] = self._serialize_dict(v)
            else:
                serialized[k] = str(v)
        
        return serialized
    
    def clear(self):
        """Clear captured signals"""
        self.signals.clear()
        logger.info("Signal capture cleared")
    
    def get_summary(self) -> Dict:
        """Get summary statistics"""
        if not self.signals:
            return {'total_signals': 0}
        
        rl_directions = [s['rl_prediction']['direction'] for s in self.signals if s.get('rl_prediction')]
        ensemble_directions = [s['ensemble_signal']['direction'] for s in self.signals if s.get('ensemble_signal')]
        
        return {
            'total_signals': len(self.signals),
            'rl_signals': len(rl_directions),
            'ensemble_signals': len(ensemble_directions),
            'rl_long': rl_directions.count('LONG'),
            'rl_short': rl_directions.count('SHORT'),
            'rl_flat': rl_directions.count('FLAT'),
            'ensemble_long': ensemble_directions.count('LONG'),
            'ensemble_short': ensemble_directions.count('SHORT'),
            'ensemble_flat': ensemble_directions.count('FLAT'),
        }

