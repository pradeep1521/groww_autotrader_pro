"""Volatility Prediction - LSTM-based IV and Historical Volatility forecasting."""

import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class VolatilityForecaster:
    """Forecast volatility using LSTM and ARIMA models."""
    
    def __init__(self):
        self.lstm_model = None
        self.arima_model = None
        self.scaler = None
        self.volatility_data = []
        
        try:
            from tensorflow import keras
            from tensorflow.keras import layers
            from statsmodels.tsa.arima.model import ARIMA
            
            self.keras = keras
            self.layers = layers
            self.ARIMA = ARIMA
            self.tf_available = True
            logger.info("✅ TensorFlow/Keras available")
        except ImportError:
            logger.warning("TensorFlow not installed. Install: pip install tensorflow")
            self.tf_available = False
        
        try:
            from sklearn.preprocessing import MinMaxScaler
            self.MinMaxScaler = MinMaxScaler
            self.sklearn_available = True
        except ImportError:
            logger.warning("scikit-learn not available")
            self.sklearn_available = False
    
    def calculate_historical_volatility(self, returns: pd.Series, 
                                       window: int = 20) -> pd.Series:
        """Calculate rolling historical volatility."""
        log_returns = np.log(returns + 1)
        volatility = log_returns.rolling(window).std() * np.sqrt(252)  # Annualized
        return volatility
    
    def calculate_parkinson_volatility(self, high_prices: pd.Series,
                                      low_prices: pd.Series,
                                      window: int = 20) -> pd.Series:
        """Calculate Parkinson volatility (range-based)."""
        hl_ratio = np.log(high_prices / low_prices)
        parkinson_vol = np.sqrt(hl_ratio ** 2 / (4 * np.log(2)))
        return parkinson_vol.rolling(window).mean() * np.sqrt(252)
    
    def calculate_garman_klass_volatility(self, df: pd.DataFrame,
                                         window: int = 20) -> pd.Series:
        """Calculate Garman-Klass volatility."""
        c = np.log(df['close'] / df['open'])
        h = np.log(df['high'] / df['close'])
        l = np.log(df['low'] / df['close'])
        
        gk = np.sqrt(0.5 * h * (h - c) + 2 * np.log(2) - 1 * l * (l - c))
        return gk.rolling(window).mean() * np.sqrt(252)
    
    def build_lstm_model(self, sequence_length: int = 60,
                        forecast_steps: int = 5) -> bool:
        """Build LSTM model for volatility prediction."""
        if not self.tf_available:
            logger.error("TensorFlow not available")
            return False
        
        try:
            self.lstm_model = self.keras.Sequential([
                self.layers.LSTM(64, activation='relu', 
                               input_shape=(sequence_length, 1),
                               return_sequences=True),
                self.layers.Dropout(0.2),
                self.layers.LSTM(32, activation='relu', return_sequences=False),
                self.layers.Dropout(0.2),
                self.layers.Dense(16, activation='relu'),
                self.layers.Dense(forecast_steps)
            ])
            
            self.lstm_model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            logger.info("✅ LSTM model built")
            return True
        
        except Exception as e:
            logger.error(f"Error building LSTM: {e}")
            return False
    
    def train_lstm(self, volatility_series: pd.Series,
                  sequence_length: int = 60,
                  forecast_steps: int = 5,
                  epochs: int = 50,
                  batch_size: int = 32) -> bool:
        """Train LSTM model."""
        if not self.build_lstm_model(sequence_length, forecast_steps):
            return False
        
        try:
            # Normalize data
            if self.sklearn_available:
                self.scaler = self.MinMaxScaler()
                scaled_data = self.scaler.fit_transform(volatility_series.values.reshape(-1, 1))
            else:
                scaled_data = (volatility_series.values - volatility_series.min()) / \
                             (volatility_series.max() - volatility_series.min())
                scaled_data = scaled_data.reshape(-1, 1)
            
            # Create sequences
            X_train, y_train = [], []
            for i in range(len(scaled_data) - sequence_length - forecast_steps):
                X_train.append(scaled_data[i:i+sequence_length])
                y_train.append(scaled_data[i+sequence_length:i+sequence_length+forecast_steps].flatten())
            
            X_train = np.array(X_train)
            y_train = np.array(y_train)
            
            # Train
            self.lstm_model.fit(
                X_train, y_train,
                epochs=epochs,
                batch_size=batch_size,
                validation_split=0.2,
                verbose=0
            )
            
            logger.info(f"✅ LSTM trained on {len(X_train)} sequences")
            return True
        
        except Exception as e:
            logger.error(f"Error training LSTM: {e}")
            return False
    
    def predict_volatility_lstm(self, recent_volatility: pd.Series,
                               forecast_steps: int = 5) -> Optional[np.ndarray]:
        """Predict future volatility using LSTM."""
        if not self.lstm_model or not self.scaler:
            return None
        
        try:
            # Normalize
            scaled = self.scaler.transform(recent_volatility.values.reshape(-1, 1))
            
            # Predict
            X = scaled[-60:].reshape(1, 60, 1)  # Last 60 days
            scaled_pred = self.lstm_model.predict(X, verbose=0)
            
            # Denormalize
            forecast = self.scaler.inverse_transform(scaled_pred)
            return forecast[0]
        
        except Exception as e:
            logger.error(f"LSTM prediction error: {e}")
            return None
    
    def train_arima(self, volatility_series: pd.Series,
                   order: Tuple[int, int, int] = (1, 1, 1)) -> bool:
        """Train ARIMA model for volatility."""
        try:
            from statsmodels.tsa.arima.model import ARIMA
            
            self.arima_model = ARIMA(volatility_series, order=order)
            self.arima_model = self.arima_model.fit()
            
            logger.info("✅ ARIMA model trained")
            return True
        
        except Exception as e:
            logger.error(f"Error training ARIMA: {e}")
            return False
    
    def predict_volatility_arima(self, steps: int = 5) -> Optional[np.ndarray]:
        """Forecast volatility using ARIMA."""
        if not self.arima_model:
            return None
        
        try:
            forecast = self.arima_model.get_forecast(steps=steps)
            return forecast.predicted_mean.values
        
        except Exception as e:
            logger.error(f"ARIMA prediction error: {e}")
            return None

class IVSurfacePredictor:
    """Predict implied volatility surface."""
    
    def __init__(self):
        self.model = None
    
    def construct_iv_surface(self, options_data: pd.DataFrame) -> Dict[str, np.ndarray]:
        """Construct IV surface from options data."""
        
        # Group by strike and expiry
        strikes = sorted(options_data['strike'].unique())
        expiries = sorted(options_data['expiry'].unique())
        
        iv_matrix = np.zeros((len(expiries), len(strikes)))
        
        for i, exp in enumerate(expiries):
            for j, strike in enumerate(strikes):
                mask = (options_data['expiry'] == exp) & (options_data['strike'] == strike)
                if mask.any():
                    iv_matrix[i, j] = options_data[mask]['iv'].iloc[0]
        
        return {
            'strikes': np.array(strikes),
            'expiries': np.array(expiries),
            'iv_matrix': iv_matrix
        }
    
    def predict_iv_surface(self, current_surface: Dict[str, np.ndarray],
                          days_forward: int = 1) -> Dict[str, np.ndarray]:
        """Predict IV surface N days forward."""
        
        # Simple mean reversion model
        historical_mean = current_surface['iv_matrix'].mean()
        mean_reversion_speed = 0.1
        
        predicted = current_surface['iv_matrix'].copy()
        predicted = predicted - mean_reversion_speed * (predicted - historical_mean)
        
        return {
            'strikes': current_surface['strikes'],
            'expiries': current_surface['expiries'],
            'iv_matrix': predicted,
            'days_forward': days_forward
        }
    
    def calculate_vol_smile_skew(self, surface: Dict) -> Dict[str, float]:
        """Calculate volatility smile and skew."""
        
        iv_matrix = surface['iv_matrix']
        strikes = surface['strikes']
        
        # Use at-the-money row (middle expiry)
        atm_row = iv_matrix[len(iv_matrix)//2, :]
        
        # Skew: difference between downside and upside volatility
        mid_idx = len(strikes) // 2
        if mid_idx > 0 and mid_idx < len(strikes) - 1:
            downside_vol = atm_row[0:mid_idx].mean()
            upside_vol = atm_row[mid_idx:].mean()
            skew = downside_vol - upside_vol
        else:
            skew = 0
        
        # Smile: how much OTM vols exceed ATM
        if mid_idx < len(strikes):
            atm_vol = atm_row[mid_idx]
            otm_vol = np.concatenate([atm_row[0:mid_idx], atm_row[mid_idx+1:]]).mean()
            smile = otm_vol - atm_vol
        else:
            smile = 0
        
        return {
            'skew': skew,
            'smile': smile,
            'mean_vol': atm_row.mean(),
            'vol_of_vol': atm_row.std()
        }

class VolatilityRegimeDetector:
    """Detect volatility regimes (low, normal, high)."""
    
    def __init__(self, window: int = 30):
        self.window = window
        self.vol_history = []
    
    def detect_regime(self, volatility: float) -> str:
        """Detect current volatility regime."""
        
        self.vol_history.append(volatility)
        
        if len(self.vol_history) < self.window:
            return 'UNKNOWN'
        
        recent_vol = np.array(self.vol_history[-self.window:])
        
        p33 = np.percentile(recent_vol, 33)
        p67 = np.percentile(recent_vol, 67)
        current = volatility
        
        if current < p33:
            return 'LOW'
        elif current < p67:
            return 'NORMAL'
        else:
            return 'HIGH'
    
    def get_regime_stats(self) -> Dict[str, float]:
        """Get volatility regime statistics."""
        
        if not self.vol_history:
            return {}
        
        vol_array = np.array(self.vol_history[-self.window:])
        
        return {
            'mean': vol_array.mean(),
            'std': vol_array.std(),
            'min': vol_array.min(),
            'max': vol_array.max(),
            'current': vol_array[-1],
            'percentile': (vol_array < vol_array[-1]).sum() / len(vol_array) * 100
        }

# Example usage
def example_volatility_forecast():
    """Example volatility forecasting."""
    
    # Mock volatility data
    dates = pd.date_range(start='2023-01-01', periods=252)
    # Simulate realistic volatility time series
    vol_data = 15 + 5 * np.sin(np.arange(252) / 20) + np.random.normal(0, 1, 252)
    vol_series = pd.Series(vol_data, index=dates)
    
    # Initialize forecaster
    forecaster = VolatilityForecaster()
    
    print("📊 Volatility Forecasting:")
    
    # Calculate different volatility measures
    hv = forecaster.calculate_historical_volatility(vol_series)
    print(f"✅ Historical Volatility calculated")
    
    # Train ARIMA
    forecaster.train_arima(hv.dropna())
    
    # ARIMA forecast
    arima_forecast = forecaster.predict_volatility_arima(steps=5)
    print(f"✅ ARIMA Forecast: {arima_forecast}")
    
    # Regime detection
    detector = VolatilityRegimeDetector()
    for vol in vol_series:
        regime = detector.detect_regime(vol)
    
    stats = detector.get_regime_stats()
    print(f"✅ Volatility Regime: {stats}")

if __name__ == "__main__":
    example_volatility_forecast()
