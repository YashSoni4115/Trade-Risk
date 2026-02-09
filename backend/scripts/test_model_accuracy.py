#!/usr/bin/env python
"""
Test Model Accuracy with K-Fold Cross-Validation
=================================================
Evaluates TariffRiskNN model accuracy using K-Fold cross-validation technique.

This script:
1. Loads the sector risk dataset
2. Performs K-Fold cross-validation (default: 5 folds)
3. Reports accuracy metrics per fold and overall
4. Shows detailed performance analysis

Usage:
    python scripts/test_model_accuracy.py
"""

import sys
import logging
from pathlib import Path
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

# Suppress TensorFlow warnings
import os
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

try:
    import tensorflow as tf
    from tensorflow import keras
    from sklearn.model_selection import KFold
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score
    TF_AVAILABLE = True
except ImportError as e:
    TF_AVAILABLE = False
    print(f"ERROR: Required packages not installed: {e}")
    print("Install with: pip install tensorflow scikit-learn")
    sys.exit(1)


class KFoldModelEvaluator:
    """K-Fold Cross-Validation evaluator for TariffRiskNN."""
    
    def __init__(self, n_splits: int = 5, random_state: int = 42):
        """
        Initialize the evaluator.
        
        Args:
            n_splits: Number of folds for cross-validation
            random_state: Random seed for reproducibility
        """
        self.n_splits = n_splits
        self.random_state = random_state
        self.results = []
        
    def _build_model(self, input_dim: int) -> keras.Sequential:
        """Build the neural network model (same architecture as TariffRiskNN)."""
        model = keras.Sequential([
            keras.layers.Input(shape=(input_dim,)),
            keras.layers.Dense(64, activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.Dropout(0.3),
            keras.layers.Dense(32, activation='relu'),
            keras.layers.BatchNormalization(),
            keras.layers.Dropout(0.2),
            keras.layers.Dense(16, activation='relu'),
            keras.layers.Dropout(0.1),
            keras.layers.Dense(1, activation='sigmoid')
        ])
        
        model.compile(
            optimizer=keras.optimizers.Adam(learning_rate=0.001),
            loss='mse',
            metrics=['mae']
        )
        
        return model
    
    def load_data(self, csv_path: str) -> Tuple[np.ndarray, np.ndarray, List[str]]:
        """Load and prepare data from CSV."""
        df = pd.read_csv(csv_path)
        
        feature_cols = [
            'exposure_us',
            'exposure_cn',
            'exposure_mx',
            'hhi_concentration',
            'export_value',
            'top_partner_share'
        ]
        target_col = 'risk_score'
        
        df = df[feature_cols + [target_col]].dropna()
        
        X = df[feature_cols].values
        y = df[target_col].values / 100.0  # Normalize to 0-1
        
        return X, y, feature_cols
    
    def evaluate_fold(self, X_train: np.ndarray, X_test: np.ndarray, 
                     y_train: np.ndarray, y_test: np.ndarray,
                     fold_num: int, epochs: int = 100) -> Dict:
        """
        Train and evaluate model on a single fold.
        
        Returns:
            Dictionary with metrics for this fold
        """
        # Scale features
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        # Build and train model
        model = self._build_model(X_train_scaled.shape[1])
        
        # Train with early stopping
        history = model.fit(
            X_train_scaled, y_train,
            validation_split=0.15,
            epochs=epochs,
            batch_size=8,
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
        
        # Predict on test set
        y_pred = model.predict(X_test_scaled, verbose=0).flatten()
        
        # Calculate metrics (convert back to 0-100 scale)
        y_test_100 = y_test * 100
        y_pred_100 = y_pred * 100
        
        mse = mean_squared_error(y_test_100, y_pred_100)
        rmse = np.sqrt(mse)
        mae = mean_absolute_error(y_test_100, y_pred_100)
        r2 = r2_score(y_test_100, y_pred_100)
        
        # Accuracy within thresholds
        errors = np.abs(y_test_100 - y_pred_100)
        within_5 = np.mean(errors <= 5) * 100
        within_10 = np.mean(errors <= 10) * 100
        
        # Epochs trained
        epochs_trained = len(history.history['loss'])
        
        return {
            'fold': fold_num,
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'r2': r2,
            'within_5_pct': within_5,
            'within_10_pct': within_10,
            'epochs_trained': epochs_trained,
            'test_size': len(y_test)
        }
    
    def run_kfold_evaluation(self, csv_path: str, epochs: int = 150) -> Dict:
        """
        Run K-Fold cross-validation on the dataset.
        
        Args:
            csv_path: Path to sector risk dataset
            epochs: Max epochs per fold
            
        Returns:
            Dictionary with overall results
        """
        print(f"\n{'='*70}")
        print(f"K-Fold Cross-Validation (K={self.n_splits})")
        print(f"{'='*70}\n")
        
        # Load data
        X, y, feature_names = self.load_data(csv_path)
        print(f"📊 Dataset: {len(X)} samples")
        print(f"📋 Features: {feature_names}")
        print(f"🎯 Target range: [{y.min()*100:.1f}, {y.max()*100:.1f}] (risk score)\n")
        
        # K-Fold splitter
        kfold = KFold(n_splits=self.n_splits, shuffle=True, random_state=self.random_state)
        
        self.results = []
        
        print(f"Training {self.n_splits} models...\n")
        print("-" * 70)
        
        for fold, (train_idx, test_idx) in enumerate(kfold.split(X), 1):
            X_train, X_test = X[train_idx], X[test_idx]
            y_train, y_test = y[train_idx], y[test_idx]
            
            print(f"📁 Fold {fold}/{self.n_splits}: Training on {len(train_idx)} samples, "
                  f"Testing on {len(test_idx)} samples...", end=" ")
            
            result = self.evaluate_fold(X_train, X_test, y_train, y_test, fold, epochs)
            self.results.append(result)
            
            print(f"✅ Done (MAE: {result['mae']:.2f}, R²: {result['r2']:.3f})")
        
        print("-" * 70)
        print()
        
        # Calculate overall metrics
        overall = self._calculate_overall_metrics()
        
        return overall
    
    def _calculate_overall_metrics(self) -> Dict:
        """Calculate overall metrics across all folds."""
        metrics = {
            'mse': np.mean([r['mse'] for r in self.results]),
            'rmse': np.mean([r['rmse'] for r in self.results]),
            'mae': np.mean([r['mae'] for r in self.results]),
            'r2': np.mean([r['r2'] for r in self.results]),
            'within_5_pct': np.mean([r['within_5_pct'] for r in self.results]),
            'within_10_pct': np.mean([r['within_10_pct'] for r in self.results]),
        }
        
        # Standard deviations
        metrics['mae_std'] = np.std([r['mae'] for r in self.results])
        metrics['r2_std'] = np.std([r['r2'] for r in self.results])
        
        return metrics
    
    def print_results(self):
        """Print detailed results table."""
        print(f"\n{'='*70}")
        print("DETAILED RESULTS BY FOLD")
        print(f"{'='*70}\n")
        
        # Header
        print(f"{'Fold':<6} {'MAE':<8} {'RMSE':<8} {'R²':<8} "
              f"{'Within 5':<10} {'Within 10':<10} {'Epochs':<8}")
        print("-" * 70)
        
        # Per-fold results
        for r in self.results:
            print(f"{r['fold']:<6} {r['mae']:<8.2f} {r['rmse']:<8.2f} {r['r2']:<8.3f} "
                  f"{r['within_5_pct']:<10.1f}% {r['within_10_pct']:<10.1f}% {r['epochs_trained']:<8}")
        
        print("-" * 70)
        
        # Overall
        overall = self._calculate_overall_metrics()
        print(f"{'Mean':<6} {overall['mae']:<8.2f} {overall['rmse']:<8.2f} "
              f"{overall['r2']:<8.3f} {overall['within_5_pct']:<10.1f}% "
              f"{overall['within_10_pct']:<10.1f}%")
        print(f"{'Std':<6} ±{overall['mae_std']:<7.2f} {'':<8} ±{overall['r2_std']:<7.3f}")
        
        print()
    
    def print_summary(self):
        """Print a summary of the evaluation."""
        overall = self._calculate_overall_metrics()
        
        print(f"\n{'='*70}")
        print("📈 MODEL ACCURACY SUMMARY")
        print(f"{'='*70}\n")
        
        print(f"  Cross-Validation Method: {self.n_splits}-Fold")
        print(f"  Total Samples: {sum(r['test_size'] for r in self.results)}")
        print()
        
        print("  📊 Key Metrics (on held-out test sets):")
        print(f"     • Mean Absolute Error (MAE):    {overall['mae']:.2f} ± {overall['mae_std']:.2f} points")
        print(f"     • Root Mean Square Error:       {overall['rmse']:.2f} points")
        print(f"     • R² Score:                     {overall['r2']:.3f} ± {overall['r2_std']:.3f}")
        print()
        
        print("  🎯 Prediction Accuracy:")
        print(f"     • Predictions within ±5 points:  {overall['within_5_pct']:.1f}%")
        print(f"     • Predictions within ±10 points: {overall['within_10_pct']:.1f}%")
        print()
        
        # Interpretation
        print("  📝 Interpretation:")
        if overall['r2'] >= 0.8:
            print("     ✅ Excellent model fit (R² ≥ 0.80)")
        elif overall['r2'] >= 0.6:
            print("     ✅ Good model fit (R² ≥ 0.60)")
        elif overall['r2'] >= 0.4:
            print("     ⚠️  Moderate model fit (R² ≥ 0.40)")
        else:
            print("     ❌ Poor model fit (R² < 0.40)")
        
        if overall['mae'] <= 5:
            print("     ✅ Very accurate predictions (MAE ≤ 5)")
        elif overall['mae'] <= 10:
            print("     ✅ Good prediction accuracy (MAE ≤ 10)")
        else:
            print("     ⚠️  Moderate prediction accuracy (MAE > 10)")
        
        print(f"\n{'='*70}\n")


def run_additional_tests(csv_path: str):
    """Run additional accuracy tests on specific scenarios."""
    print(f"\n{'='*70}")
    print("ADDITIONAL ACCURACY TESTS")
    print(f"{'='*70}\n")
    
    from src.ml_model import TariffRiskNN
    
    # Train a full model
    print("Training model on full dataset for scenario tests...")
    model = TariffRiskNN()
    model.train(csv_path, epochs=100, batch_size=8)
    print()
    
    # Test scenarios
    test_cases = [
        {
            "name": "High US Exposure Sector (e.g., Automotive)",
            "features": {
                'exposure_us': 0.95,
                'exposure_cn': 0.02,
                'exposure_mx': 0.01,
                'hhi_concentration': 0.90,
                'export_value': 50_000_000_000,
                'top_partner_share': 0.95
            },
            "expected_range": (70, 100),
            "rationale": "Very high US dependency should indicate high tariff risk"
        },
        {
            "name": "Diversified Sector (e.g., Machinery)",
            "features": {
                'exposure_us': 0.35,
                'exposure_cn': 0.25,
                'exposure_mx': 0.15,
                'hhi_concentration': 0.40,
                'export_value': 20_000_000_000,
                'top_partner_share': 0.40
            },
            "expected_range": (30, 60),
            "rationale": "Diversified exports should show moderate risk"
        },
        {
            "name": "Low Exposure Sector (e.g., Services)",
            "features": {
                'exposure_us': 0.20,
                'exposure_cn': 0.15,
                'exposure_mx': 0.10,
                'hhi_concentration': 0.25,
                'export_value': 5_000_000_000,
                'top_partner_share': 0.25
            },
            "expected_range": (10, 40),
            "rationale": "Low exposure and diversification should show low risk"
        },
        {
            "name": "China-Heavy Sector",
            "features": {
                'exposure_us': 0.10,
                'exposure_cn': 0.80,
                'exposure_mx': 0.02,
                'hhi_concentration': 0.85,
                'export_value': 30_000_000_000,
                'top_partner_share': 0.80
            },
            "expected_range": (40, 80),
            "rationale": "High China exposure with concentration creates moderate-high risk"
        },
        {
            "name": "Mexico-Focused Sector",
            "features": {
                'exposure_us': 0.25,
                'exposure_cn': 0.05,
                'exposure_mx': 0.60,
                'hhi_concentration': 0.70,
                'export_value': 15_000_000_000,
                'top_partner_share': 0.60
            },
            "expected_range": (35, 65),
            "rationale": "USMCA provides some protection but concentration is a concern"
        }
    ]
    
    print("-" * 70)
    print(f"{'Test Case':<35} {'Predicted':>10} {'Expected':>15} {'Result':>10}")
    print("-" * 70)
    
    passed = 0
    total = len(test_cases)
    
    for tc in test_cases:
        pred = model.predict(tc['features'])
        exp_low, exp_high = tc['expected_range']
        in_range = exp_low <= pred <= exp_high
        
        status = "✅ PASS" if in_range else "⚠️  CHECK"
        if in_range:
            passed += 1
        
        print(f"{tc['name']:<35} {pred:>10.1f} {f'{exp_low}-{exp_high}':>15} {status:>10}")
    
    print("-" * 70)
    print(f"\nScenario Tests: {passed}/{total} passed")
    print()
    
    # Print detailed analysis
    print("\n📋 Detailed Scenario Analysis:\n")
    for tc in test_cases:
        pred = model.predict(tc['features'])
        exp_low, exp_high = tc['expected_range']
        in_range = exp_low <= pred <= exp_high
        
        print(f"  {tc['name']}:")
        print(f"    Prediction: {pred:.1f}")
        print(f"    Expected:   {exp_low}-{exp_high}")
        print(f"    Rationale:  {tc['rationale']}")
        print()


def main():
    """Main function to run K-Fold evaluation."""
    print()
    print("╔═══════════════════════════════════════════════════════════════════════╗")
    print("║      TradeRisk ML Model - Accuracy Testing with K-Fold CV            ║")
    print("╚═══════════════════════════════════════════════════════════════════════╝")
    print()
    
    # Paths
    data_csv = BACKEND_DIR / 'data' / 'processed' / 'sector_risk_dataset.csv'
    
    if not data_csv.exists():
        print(f"❌ ERROR: Data file not found: {data_csv}")
        sys.exit(1)
    
    # Run K-Fold evaluation
    evaluator = KFoldModelEvaluator(n_splits=5, random_state=42)
    evaluator.run_kfold_evaluation(str(data_csv), epochs=150)
    evaluator.print_results()
    evaluator.print_summary()
    
    # Run additional scenario tests
    run_additional_tests(str(data_csv))
    
    print("\n✅ All accuracy tests complete!\n")
    return 0


if __name__ == '__main__':
    sys.exit(main())
