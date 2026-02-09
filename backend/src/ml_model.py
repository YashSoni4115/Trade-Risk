"""
TradeRisk ML Model
====================
Neural network for predicting tariff impact risk.
Trained on historical sector trade data and tariff scenarios.
"""

import numpy as np
import pandas as pd
from pathlib import Path
import pickle
import logging
from functools import lru_cache
from typing import Tuple, Dict, List, Any

try:
    import tensorflow as tf
    from tensorflow import keras  # type: ignore
    from sklearn.preprocessing import StandardScaler
    from sklearn.model_selection import train_test_split
    TENSORFLOW_AVAILABLE = True
    layers = keras.layers
    models = keras.models
except ImportError:
    TENSORFLOW_AVAILABLE = False
    tf = None
    keras = None
    StandardScaler = None
    layers = None
    models = None


logger = logging.getLogger(__name__)


class TariffRiskNN:
    """Neural network for predicting tariff impact risk scores."""
    def __init__(self, model_path: str = None):
        """
        Initialize the NN model.
        
        Args:
            model_path: Path to saved model (optional)
        """
        if not TENSORFLOW_AVAILABLE:
            raise ImportError("TensorFlow and scikit-learn required for ML model")
        
        self.model = None
        self.scaler = StandardScaler()
        self.is_trained = False
        self.model_path = model_path
        self._prediction_cache = {}  # Simple prediction cache
        
        if model_path and Path(model_path).exists():
            self.load_model(model_path)
    
    def _build_model(self, input_dim: int) -> Any:
        """
        Build neural network architecture.
        
        Input features: tariff%, exposure_us, exposure_cn, exposure_eu, 
                       concentration, export_value, hhi
        Output: predicted risk score (0-100)
        """
        model = models.Sequential([
            layers.Input(shape=(input_dim,)),
            
            # Balanced architecture with moderate regularization
            layers.Dense(64, activation='relu', name='dense_1'),
            layers.Dropout(0.2),
            
            layers.Dense(32, activation='relu', name='dense_2'),
            layers.Dropout(0.15),
            
            layers.Dense(16, activation='relu', name='dense_3'),
            
            # Output layer (bounded 0-100)
            layers.Dense(1, activation='sigmoid', name='output')
        ])
        
        # Scale sigmoid output to 0-100
        model = models.Sequential(model.layers)
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def prepare_data(self, csv_path: str) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """
        Prepare training data from sector risk dataset.
        
        Args:
            csv_path: Path to sector_risk_dataset.csv
            
        Returns:
            X, y, feature_names
        """
        df = pd.read_csv(csv_path)
        
        # Select features for the model
        # NOTE: tariff_percent is excluded because it's constant (all 10.0) in current dataset
        # To include it, we'd need training data with varying tariff percentages
        feature_cols = [
            'exposure_us',      # US exposure (0-1)
            'exposure_cn',      # China exposure (0-1)
            'exposure_mx',      # Mexico exposure
            'hhi_concentration', # HHI concentration (0-1)
            'export_value',     # Total exports
            'top_partner_share' # Top partner concentration (0-1)
        ]
        
        # Target: actual risk score from deterministic engine
        target_col = 'risk_score'
        
        # Remove rows with missing values
        df = df[feature_cols + [target_col]].dropna()
        
        X = df[feature_cols].values
        y = df[target_col].values / 100.0  # Normalize to 0-1 for sigmoid
        
        # Log statistics
        logger.info(f"Prepared {len(X)} training samples")
        logger.info(f"Features: {feature_cols}")
        logger.info(f"Target range: [{y.min():.4f}, {y.max():.4f}]")
        
        return X, y, feature_cols
    
    def train(self, csv_path: str, epochs: int = 120, batch_size: int = 16, 
              validation_split: float = 0.2) -> Dict:
        """
        Train the neural network on sector data.
        
        Args:
            csv_path: Path to sector_risk_dataset.csv
            epochs: Number of training epochs
            batch_size: Batch size
            validation_split: Validation split ratio
            
        Returns:
            Training history
        """
        logger.info("Preparing training data...")
        X, y, self.feature_names = self.prepare_data(csv_path)
        
        # Scale features
        logger.info("Scaling features...")
        X_scaled = self.scaler.fit_transform(X)
        
        # Split data
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=validation_split, random_state=42
        )
        
        # Build model
        logger.info("Building model...")
        self.model = self._build_model(X_scaled.shape[1])
        
        # Train with early stopping for balanced performance
        logger.info(f"Training for {epochs} epochs...")
        history = self.model.fit(
            X_train, y_train,
            validation_data=(X_val, y_val),
            epochs=epochs,
            batch_size=batch_size,
            verbose=0,
            callbacks=[
                keras.callbacks.EarlyStopping(
                    monitor='val_loss',
                    patience=15,
                    restore_best_weights=True,
                    verbose=0
                )
            ]
        )
        
        self.is_trained = True
        
        # Log final metrics
        final_train_loss = history.history['loss'][-1]
        final_train_mae = history.history['mae'][-1]
        final_val_loss = history.history['val_loss'][-1]
        final_val_mae = history.history['val_mae'][-1]
        logger.info(f"Final train loss: {final_train_loss:.6f}, train MAE: {final_train_mae:.6f}")
        logger.info(f"Final val loss: {final_val_loss:.6f}, val MAE: {final_val_mae:.6f}")
        
        return history.history
    
    def predict(self, features: Dict) -> float:
        """
        Predict risk score for given sector features.
        
        Args:
            features: Dict with keys matching training features
            
        Returns:
            Predicted risk score (0-100)
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        # Check cache first (using sorted tuple as key for hashability)
        cache_key = tuple(sorted(features.items()))
        if cache_key in self._prediction_cache:
            return self._prediction_cache[cache_key]
        
        # Build feature vector in correct order
        # NOTE: tariff_percent excluded - it has zero variance (always 10.0) in dataset
        # To include it, would need training data with varying tariff values
        feature_vector = np.array([
            features.get('exposure_us', 0.0),
            features.get('exposure_cn', 0.0),
            features.get('exposure_mx', 0.0),
            features.get('hhi_concentration', 0.0),
            features.get('export_value', 1e9),  # Default 1B
            features.get('top_partner_share', 0.5)
        ]).reshape(1, -1)
        
        # Scale
        feature_vector = self.scaler.transform(feature_vector)
        
        # Predict
        pred = self.model.predict(feature_vector, verbose=0)[0][0]
        
        # Scale back to 0-100
        result = float(pred * 100.0)
        
        # Cache result (limit cache size to 1000 entries)
        if len(self._prediction_cache) < 1000:
            self._prediction_cache[cache_key] = result
        
        return result
    
    def predict_batch(self, features_list: List[Dict]) -> List[float]:
        """
        Predict risk scores for multiple sectors.
        
        Args:
            features_list: List of feature dicts
            
        Returns:
            List of risk scores
        """
        if not self.is_trained or self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        if not features_list:
            return []
        
        # Vectorized batch prediction (much faster than individual calls)
        feature_matrix = np.array([
            [
                f.get('exposure_us', 0.0),
                f.get('exposure_cn', 0.0),
                f.get('exposure_mx', 0.0),
                f.get('hhi_concentration', 0.0),
                f.get('export_value', 1e9),
                f.get('top_partner_share', 0.5)
            ]
            for f in features_list
        ])
        
        # Scale all at once
        feature_matrix_scaled = self.scaler.transform(feature_matrix)
        
        # Batch predict
        predictions = self.model.predict(feature_matrix_scaled, verbose=0)
        
        # Scale back to 0-100
        return [float(pred[0] * 100.0) for pred in predictions]
    
    def save_model(self, path: str):
        """Save trained model and scaler."""
        if not self.is_trained:
            raise ValueError("Model not trained")
        
        path = Path(path)
        path.mkdir(parents=True, exist_ok=True)
        
        self.model.save(str(path / 'model.h5'))
        
        with open(path / 'scaler.pkl', 'wb') as f:
            pickle.dump(self.scaler, f)
        
        logger.info(f"Model saved to {path}")
    
    def load_model(self, path: str):
        """Load trained model and scaler."""
        path = Path(path)
        
        self.model = keras.models.load_model(str(path / 'model.h5'))
        
        with open(path / 'scaler.pkl', 'rb') as f:
            self.scaler = pickle.load(f)
        
        self.is_trained = True
        logger.info(f"Model loaded from {path}")


def train_and_save_model(csv_path: str, output_dir: str = None) -> TariffRiskNN:
    """
    Convenience function to train model and save it.
    
    Args:
        csv_path: Path to sector_risk_dataset.csv
        output_dir: Where to save model (default: ./models/tariff_risk_nn)
        
    Returns:
        Trained model instance
    """
    if output_dir is None:
        output_dir = Path(__file__).parent.parent / 'models' / 'tariff_risk_nn'
    
    model = TariffRiskNN()
    model.train(csv_path, epochs=150)
    model.save_model(output_dir)
    
    return model
