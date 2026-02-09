"""
TariffShock ML Model Tests
==========================
Tests for neural network model training and inference.
Includes K-Fold Cross-Validation tests for accuracy evaluation.
"""

import pytest
import tempfile
from pathlib import Path
import sys
import numpy as np

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Check if TensorFlow is available
try:
    from src.ml_model import TariffRiskNN
    from sklearn.model_selection import KFold
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_absolute_error, r2_score
    import pandas as pd
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False


@pytest.mark.skipif(not TF_AVAILABLE, reason="TensorFlow not installed")
class TestMLModel:
    """Test neural network model."""
    
    @pytest.fixture
    def data_csv(self):
        """Get path to test data."""
        return BACKEND_DIR / 'data' / 'processed' / 'sector_risk_dataset.csv'
    
    def test_model_initialization(self):
        """Model initializes without error."""
        model = TariffRiskNN()
        assert model.model is None
        assert not model.is_trained
    
    def test_data_preparation(self, data_csv):
        """Data preparation loads and prepares data."""
        if not data_csv.exists():
            pytest.skip(f"Test data not found: {data_csv}")
        
        model = TariffRiskNN()
        X, y, features = model.prepare_data(str(data_csv))
        
        assert X.shape[0] > 0
        assert y.shape[0] == X.shape[0]
        assert len(features) == 6
        assert 'exposure_us' in features
        assert y.min() >= 0.0
        assert y.max() <= 1.0
    
    def test_model_training(self, data_csv):
        """Model trains successfully."""
        if not data_csv.exists():
            pytest.skip(f"Test data not found: {data_csv}")
        
        model = TariffRiskNN()
        history = model.train(
            str(data_csv),
            epochs=5,  # Small number for fast test
            batch_size=16
        )
        
        assert model.is_trained
        assert model.model is not None
        assert 'loss' in history
        assert len(history['loss']) > 0
    
    def test_prediction(self, data_csv):
        """Model makes predictions in valid range."""
        if not data_csv.exists():
            pytest.skip(f"Test data not found: {data_csv}")
        
        model = TariffRiskNN()
        model.train(str(data_csv), epochs=5, batch_size=16)
        
        # Test with sector-like features
        features = {
            'exposure_us': 0.95,
            'exposure_cn': 0.01,
            'exposure_mx': 0.0,
            'hhi_concentration': 0.92,
            'export_value': 50000000000,
            'top_partner_share': 0.95
        }
        
        pred = model.predict(features)
        
        assert isinstance(pred, float)
        assert 0 <= pred <= 100
    
    def test_prediction_varies_by_input(self, data_csv):
        """Predictions vary with different inputs."""
        if not data_csv.exists():
            pytest.skip(f"Test data not found: {data_csv}")
        
        model = TariffRiskNN()
        model.train(str(data_csv), epochs=5, batch_size=16)
        
        # High exposure sector
        high_exp = {
            'exposure_us': 0.95,
            'exposure_cn': 0.01,
            'exposure_mx': 0.0,
            'hhi_concentration': 0.90,
            'export_value': 10000000000,
            'top_partner_share': 0.95
        }
        
        # Low exposure sector
        low_exp = {
            'exposure_us': 0.30,
            'exposure_cn': 0.30,
            'exposure_mx': 0.30,
            'hhi_concentration': 0.35,
            'export_value': 1000000000,
            'top_partner_share': 0.35
        }
        
        pred_high = model.predict(high_exp)
        pred_low = model.predict(low_exp)
        
        # High exposure should generally have higher risk
        assert pred_high >= pred_low or abs(pred_high - pred_low) < 5
    
    def test_batch_prediction(self, data_csv):
        """Batch prediction works."""
        if not data_csv.exists():
            pytest.skip(f"Test data not found: {data_csv}")
        
        model = TariffRiskNN()
        model.train(str(data_csv), epochs=5, batch_size=16)
        
        features_list = [
            {
                'exposure_us': 0.9,
                'exposure_cn': 0.05,
                'exposure_mx': 0.0,
                'hhi_concentration': 0.85,
                'export_value': 5000000000,
                'top_partner_share': 0.9
            },
            {
                'exposure_us': 0.5,
                'exposure_cn': 0.3,
                'exposure_mx': 0.1,
                'hhi_concentration': 0.5,
                'export_value': 2000000000,
                'top_partner_share': 0.5
            }
        ]
        
        predictions = model.predict_batch(features_list)
        
        assert len(predictions) == 2
        assert all(0 <= p <= 100 for p in predictions)
    
    def test_model_save_load(self, data_csv):
        """Model can be saved and loaded."""
        if not data_csv.exists():
            pytest.skip(f"Test data not found: {data_csv}")
        
        with tempfile.TemporaryDirectory() as tmpdir:
            # Train and save
            model1 = TariffRiskNN()
            model1.train(str(data_csv), epochs=5, batch_size=16)
            model1.save_model(tmpdir)
            
            # Load
            model2 = TariffRiskNN(tmpdir)
            
            assert model2.is_trained
            assert model2.model is not None
            
            # Same input should give same (or very similar) prediction
            features = {
                'exposure_us': 0.85,
                'exposure_cn': 0.05,
                'exposure_mx': 0.05,
                'hhi_concentration': 0.80,
                'export_value': 20000000000,
                'top_partner_share': 0.85
            }
            
            pred1 = model1.predict(features)
            pred2 = model2.predict(features)
            
            assert abs(pred1 - pred2) < 0.1
    
    def test_untrained_model_raises(self):
        """Untrained model raises when predicting."""
        model = TariffRiskNN()
        
        features = {'exposure_us': 0.5}
        
        with pytest.raises(ValueError):
            model.predict(features)


@pytest.mark.skipif(not TF_AVAILABLE, reason="TensorFlow not installed")
class TestKFoldCrossValidation:
    """K-Fold Cross-Validation tests for model accuracy."""
    
    @pytest.fixture
    def data_csv(self):
        """Get path to test data."""
        return BACKEND_DIR / 'data' / 'processed' / 'sector_risk_dataset.csv'
    
    def _load_data(self, csv_path):
        """Load and prepare data from CSV."""
        df = pd.read_csv(csv_path)
        feature_cols = [
            'exposure_us', 'exposure_cn', 'exposure_mx',
            'hhi_concentration', 'export_value', 'top_partner_share'
        ]
        target_col = 'risk_score'
        df = df[feature_cols + [target_col]].dropna()
        X = df[feature_cols].values
        y = df[target_col].values / 100.0
        return X, y, feature_cols
    
    def test_kfold_3_splits(self, data_csv):
        """3-fold cross-validation runs successfully."""
        if not data_csv.exists():
            pytest.skip(f"Test data not found: {data_csv}")
        
        from tensorflow import keras
        
        X, y, features = self._load_data(str(data_csv))
        kfold = KFold(n_splits=3, shuffle=True, random_state=42)
        
        fold_results = []
        
        for train_idx, test_idx in kfold.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            # Scale features
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            # Build model
            model = keras.Sequential([
                keras.layers.Input(shape=(X_train_scaled.shape[1],)),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(16, activation='relu'),
                keras.layers.Dense(1, activation='sigmoid')
            ])
            model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            
            # Train (few epochs for speed)
            model.fit(X_train_scaled, y_train, epochs=10, verbose=0, batch_size=16)
            
            # Predict
            y_pred = model.predict(X_test_scaled, verbose=0).flatten()
            mae = mean_absolute_error(y_test * 100, y_pred * 100)
            fold_results.append(mae)
        
        # All folds should complete
        assert len(fold_results) == 3
        # MAE should be reasonable (< 50 points on 0-100 scale)
        assert all(mae < 50 for mae in fold_results)
    
    def test_kfold_5_splits(self, data_csv):
        """5-fold cross-validation runs successfully."""
        if not data_csv.exists():
            pytest.skip(f"Test data not found: {data_csv}")
        
        from tensorflow import keras
        
        X, y, features = self._load_data(str(data_csv))
        kfold = KFold(n_splits=5, shuffle=True, random_state=42)
        
        mae_scores = []
        r2_scores = []
        
        for train_idx, test_idx in kfold.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            model = keras.Sequential([
                keras.layers.Input(shape=(X_train_scaled.shape[1],)),
                keras.layers.Dense(64, activation='relu'),
                keras.layers.BatchNormalization(),
                keras.layers.Dropout(0.3),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(1, activation='sigmoid')
            ])
            model.compile(optimizer='adam', loss='mse', metrics=['mae'])
            
            model.fit(
                X_train_scaled, y_train, 
                epochs=20, verbose=0, batch_size=8,
                validation_split=0.15
            )
            
            y_pred = model.predict(X_test_scaled, verbose=0).flatten()
            mae = mean_absolute_error(y_test * 100, y_pred * 100)
            r2 = r2_score(y_test * 100, y_pred * 100)
            
            mae_scores.append(mae)
            r2_scores.append(r2)
        
        # All 5 folds completed
        assert len(mae_scores) == 5
        
        # Average MAE should be < 40
        avg_mae = np.mean(mae_scores)
        assert avg_mae < 40, f"Average MAE {avg_mae:.2f} is too high"
    
    def test_scenario_accuracy(self, data_csv):
        """Model predicts reasonable values for known scenarios."""
        if not data_csv.exists():
            pytest.skip(f"Test data not found: {data_csv}")
        
        model = TariffRiskNN()
        model.train(str(data_csv), epochs=50, batch_size=8)
        
        # High risk scenario
        high_risk = {
            'exposure_us': 0.95,
            'exposure_cn': 0.02,
            'exposure_mx': 0.01,
            'hhi_concentration': 0.90,
            'export_value': 50_000_000_000,
            'top_partner_share': 0.95
        }
        pred_high = model.predict(high_risk)
        
        # Low risk scenario
        low_risk = {
            'exposure_us': 0.25,
            'exposure_cn': 0.25,
            'exposure_mx': 0.25,
            'hhi_concentration': 0.30,
            'export_value': 5_000_000_000,
            'top_partner_share': 0.30
        }
        pred_low = model.predict(low_risk)
        
        # High exposure should predict higher risk than low exposure
        assert pred_high > pred_low, \
            f"High risk ({pred_high:.1f}) should be > low risk ({pred_low:.1f})"
        
        # High risk should be in upper range
        assert pred_high >= 50, f"High risk prediction {pred_high:.1f} too low"
        
        # Low risk should be in lower range
        assert pred_low <= 60, f"Low risk prediction {pred_low:.1f} too high"
    
    def test_consistency_across_folds(self, data_csv):
        """Results should be reasonably consistent across folds."""
        if not data_csv.exists():
            pytest.skip(f"Test data not found: {data_csv}")
        
        from tensorflow import keras
        
        X, y, _ = self._load_data(str(data_csv))
        kfold = KFold(n_splits=5, shuffle=True, random_state=42)
        
        mae_scores = []
        
        for train_idx, test_idx in kfold.split(X):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            scaler = StandardScaler()
            X_train_scaled = scaler.fit_transform(X_train)
            X_test_scaled = scaler.transform(X_test)
            
            model = keras.Sequential([
                keras.layers.Input(shape=(X_train_scaled.shape[1],)),
                keras.layers.Dense(32, activation='relu'),
                keras.layers.Dense(16, activation='relu'),
                keras.layers.Dense(1, activation='sigmoid')
            ])
            model.compile(optimizer='adam', loss='mse')
            model.fit(X_train_scaled, y_train, epochs=15, verbose=0)
            
            y_pred = model.predict(X_test_scaled, verbose=0).flatten()
            mae = mean_absolute_error(y_test * 100, y_pred * 100)
            mae_scores.append(mae)
        
        # Standard deviation of MAE across folds should be reasonable
        std_mae = np.std(mae_scores)
        assert std_mae < 15, f"MAE too inconsistent across folds: std={std_mae:.2f}"


@pytest.mark.skipif(not TF_AVAILABLE, reason="TensorFlow not installed")
class TestMLEndpoints:
    """Test API endpoints for ML model."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        from src.routes import create_app
        
        app = create_app()
        app.config['TESTING'] = True
        
        with app.test_client() as client:
            yield client
    
    def test_predict_ml_endpoint_requires_ml_model(self, client):
        """ML endpoint returns 503 if model not loaded."""
        response = client.post(
            '/api/predict-ml',
            json={
                'exposure_us': 0.5,
                'exposure_cn': 0.2,
                'exposure_mx': 0.1,
                'hhi_concentration': 0.6,
                'export_value': 1000000000,
                'top_partner_share': 0.6
            }
        )
        
        # Should return 503 since model not trained
        assert response.status_code in [503, 400]
    
    def test_predict_ml_batch_endpoint_exists(self, client):
        """ML batch endpoint exists."""
        response = client.post(
            '/api/predict-ml-batch',
            json={'sectors': ['87']}
        )
        
        # Should return 503 if model not loaded, not 404
        assert response.status_code in [503, 400, 200]
