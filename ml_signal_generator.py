"""ML Signal Generation - Machine learning-based trading signals."""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MLSignal:
    """ML-generated trading signal."""
    symbol: str
    timestamp: datetime
    signal_type: str  # BUY, SELL, HOLD
    confidence: float  # 0-1
    features_used: List[str]
    model_name: str
    score: float
    explanation: str

class FeatureEngineer:
    """Generate ML features from OHLCV data."""
    
    @staticmethod
    def calculate_returns(close_prices: pd.Series, periods: List[int] = [1, 5, 10]) -> pd.DataFrame:
        """Calculate return features."""
        features = {}
        for period in periods:
            features[f'return_{period}d'] = close_prices.pct_change(period)
        return pd.DataFrame(features)
    
    @staticmethod
    def calculate_volatility(close_prices: pd.Series, window: int = 20) -> pd.Series:
        """Calculate rolling volatility."""
        log_returns = np.log(close_prices / close_prices.shift(1))
        return log_returns.rolling(window).std()
    
    @staticmethod
    def calculate_momentum(close_prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate momentum (ROC)."""
        return (close_prices - close_prices.shift(period)) / close_prices.shift(period)
    
    @staticmethod
    def calculate_rsi(close_prices: pd.Series, period: int = 14) -> pd.Series:
        """Calculate Relative Strength Index."""
        delta = close_prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(close_prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        """Calculate MACD."""
        ema_fast = close_prices.ewm(span=fast).mean()
        ema_slow = close_prices.ewm(span=slow).mean()
        macd = ema_fast - ema_slow
        signal_line = macd.ewm(span=signal).mean()
        histogram = macd - signal_line
        
        return pd.DataFrame({
            'macd': macd,
            'signal_line': signal_line,
            'histogram': histogram
        })
    
    @staticmethod
    def calculate_bollinger_bands(close_prices: pd.Series, window: int = 20, 
                                 num_std: float = 2) -> pd.DataFrame:
        """Calculate Bollinger Bands."""
        sma = close_prices.rolling(window).mean()
        std = close_prices.rolling(window).std()
        
        return pd.DataFrame({
            'upper_band': sma + (std * num_std),
            'middle_band': sma,
            'lower_band': sma - (std * num_std),
            'bb_position': (close_prices - (sma - std * num_std)) / (2 * std * num_std)
        })
    
    @staticmethod
    def create_feature_set(df: pd.DataFrame) -> pd.DataFrame:
        """Create comprehensive feature set."""
        features = pd.DataFrame()
        
        # Price-based features
        features['close'] = df['close']
        features['volume'] = df['volume']
        features['volume_change'] = df['volume'].pct_change()
        
        # Returns and volatility
        features['return_5d'] = df['close'].pct_change(5)
        features['volatility_20d'] = FeatureEngineer.calculate_volatility(df['close'], 20)
        
        # Momentum
        features['momentum_14'] = FeatureEngineer.calculate_momentum(df['close'], 14)
        features['rsi_14'] = FeatureEngineer.calculate_rsi(df['close'], 14)
        
        # MACD
        macd = FeatureEngineer.calculate_macd(df['close'])
        features['macd'] = macd['macd']
        features['macd_signal'] = macd['signal_line']
        
        # Bollinger Bands
        bb = FeatureEngineer.calculate_bollinger_bands(df['close'])
        features['bb_position'] = bb['bb_position']
        
        # Price patterns
        features['price_range'] = (df['high'] - df['low']) / df['close']
        features['is_up_day'] = (df['close'] > df['open']).astype(int)
        
        # Volume patterns
        features['volume_sma_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        return features.dropna()

class SignalGenerator:
    """Generate trading signals using ML models."""
    
    def __init__(self):
        self.models = {}
        self.feature_engineer = FeatureEngineer()
        self.scaler = None
        
        try:
            from sklearn.preprocessing import StandardScaler
            from sklearn.ensemble import RandomForestClassifier
            from sklearn.svm import SVC
            self.sklearn_available = True
            self.StandardScaler = StandardScaler
            self.RandomForestClassifier = RandomForestClassifier
            self.SVC = SVC
        except ImportError:
            logger.warning("scikit-learn not installed. Install: pip install scikit-learn")
            self.sklearn_available = False
    
    def train_random_forest(self, X_train: np.ndarray, y_train: np.ndarray,
                           n_estimators: int = 100) -> bool:
        """Train Random Forest model."""
        if not self.sklearn_available:
            return False
        
        try:
            self.models['random_forest'] = self.RandomForestClassifier(
                n_estimators=n_estimators,
                max_depth=10,
                random_state=42
            )
            self.models['random_forest'].fit(X_train, y_train)
            
            logger.info(f"✅ Random Forest trained on {len(X_train)} samples")
            return True
        except Exception as e:
            logger.error(f"Error training Random Forest: {e}")
            return False
    
    def train_svm(self, X_train: np.ndarray, y_train: np.ndarray) -> bool:
        """Train Support Vector Machine model."""
        if not self.sklearn_available:
            return False
        
        try:
            self.models['svm'] = self.SVC(kernel='rbf', probability=True)
            self.models['svm'].fit(X_train, y_train)
            
            logger.info(f"✅ SVM trained on {len(X_train)} samples")
            return True
        except Exception as e:
            logger.error(f"Error training SVM: {e}")
            return False
    
    def predict_signal(self, features: pd.DataFrame, model_name: str = 'random_forest') -> Optional[MLSignal]:
        """Generate ML signal from features."""
        if not self.sklearn_available or model_name not in self.models:
            return None
        
        try:
            # Get latest features
            X = features.iloc[-1:].values
            
            model = self.models[model_name]
            
            # Predict
            prediction = model.predict(X)[0]
            probabilities = model.predict_proba(X)[0]
            confidence = max(probabilities)
            
            # Map prediction to signal
            signal_map = {0: 'SELL', 1: 'HOLD', 2: 'BUY'}
            signal_type = signal_map.get(prediction, 'HOLD')
            
            # Feature importance
            if hasattr(model, 'feature_importances_'):
                top_features = np.argsort(model.feature_importances_)[-3:]
                features_used = [features.columns[i] for i in top_features]
            else:
                features_used = list(features.columns)[:3]
            
            return MLSignal(
                symbol='NIFTY50',
                timestamp=datetime.now(),
                signal_type=signal_type,
                confidence=float(confidence),
                features_used=features_used,
                model_name=model_name,
                score=float(probabilities[2]),  # BUY probability
                explanation=f"{signal_type} signal with {confidence*100:.1f}% confidence"
            )
        
        except Exception as e:
            logger.error(f"Error generating signal: {e}")
            return None

class EnsembleSignalGenerator:
    """Combine signals from multiple models."""
    
    def __init__(self):
        self.generators = {}
    
    def register_generator(self, name: str, generator: SignalGenerator):
        """Register a signal generator."""
        self.generators[name] = generator
    
    def generate_ensemble_signal(self, features: pd.DataFrame) -> Dict:
        """Generate ensemble signal."""
        signals = []
        
        for name, generator in self.generators.items():
            signal = generator.predict_signal(features)
            if signal:
                signals.append(signal)
        
        if not signals:
            return {'signal': 'HOLD', 'confidence': 0}
        
        # Weighted voting
        buy_votes = sum(1 for s in signals if s.signal_type == 'BUY')
        sell_votes = sum(1 for s in signals if s.signal_type == 'SELL')
        
        avg_confidence = np.mean([s.confidence for s in signals])
        
        if buy_votes > sell_votes:
            ensemble_signal = 'BUY'
        elif sell_votes > buy_votes:
            ensemble_signal = 'SELL'
        else:
            ensemble_signal = 'HOLD'
        
        return {
            'signal': ensemble_signal,
            'confidence': avg_confidence,
            'model_count': len(signals),
            'buy_votes': buy_votes,
            'sell_votes': sell_votes,
            'individual_signals': [s.to_dict() if hasattr(s, 'to_dict') else s.__dict__ for s in signals]
        }

class AnomalyDetector:
    """Detect anomalies in price/volume patterns."""
    
    def __init__(self, contamination: float = 0.05):
        self.contamination = contamination
        self.model = None
        
        try:
            from sklearn.ensemble import IsolationForest
            self.IsolationForest = IsolationForest
            self.sklearn_available = True
        except ImportError:
            logger.warning("scikit-learn required for anomaly detection")
            self.sklearn_available = False
    
    def train(self, X: np.ndarray) -> bool:
        """Train anomaly detector."""
        if not self.sklearn_available:
            return False
        
        try:
            self.model = self.IsolationForest(
                contamination=self.contamination,
                random_state=42
            )
            self.model.fit(X)
            logger.info("✅ Anomaly detector trained")
            return True
        except Exception as e:
            logger.error(f"Error training anomaly detector: {e}")
            return False
    
    def detect_anomalies(self, X: np.ndarray) -> np.ndarray:
        """Detect anomalies."""
        if not self.model:
            return np.zeros(len(X), dtype=bool)
        
        predictions = self.model.predict(X)
        return predictions == -1  # -1 = anomaly

# Example usage
def example_ml_signals():
    """Example ML signal generation."""
    
    # Mock OHLCV data
    dates = pd.date_range(start='2023-01-01', periods=100)
    df = pd.DataFrame({
        'timestamp': dates,
        'open': 100 + np.cumsum(np.random.randn(100) * 2),
        'high': 102 + np.cumsum(np.random.randn(100) * 2),
        'low': 98 + np.cumsum(np.random.randn(100) * 2),
        'close': 100 + np.cumsum(np.random.randn(100) * 2),
        'volume': np.random.randint(1000000, 5000000, 100)
    })
    
    # Create features
    engineer = FeatureEngineer()
    features = engineer.create_feature_set(df)
    
    print("📊 Feature Engineering:")
    print(f"✅ Created {len(features.columns)} features")
    print(f"✅ Features: {list(features.columns)}")
    
    # Generate signal
    generator = SignalGenerator()
    
    # Mock training data
    X_train = features.iloc[:80].values
    # Buy if close > 200 MA
    y_train = (df['close'].iloc[:80] > df['close'].iloc[:80].rolling(20).mean()).astype(int)
    y_train = np.where(y_train == 1, 2, 0)  # Convert to multi-class
    
    generator.train_random_forest(X_train, y_train)
    
    signal = generator.predict_signal(features)
    if signal:
        print(f"\n🎯 Signal Generated:")
        print(f"  Type: {signal.signal_type}")
        print(f"  Confidence: {signal.confidence*100:.1f}%")
        print(f"  Features: {signal.features_used}")

if __name__ == "__main__":
    example_ml_signals()
