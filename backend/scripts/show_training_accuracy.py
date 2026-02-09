#!/usr/bin/env python
"""
Show Training Set Accuracy (for hackathon demo)
================================================
Demonstrates model performance on training data after overfitting.
"""

import sys
from pathlib import Path
import numpy as np
import pandas as pd

BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from src.ml_model import TariffRiskNN
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

def main():
    print("\n" + "="*70)
    print("TRAINING SET ACCURACY (Production Model)")
    print("="*70 + "\n")
    
    # Train fresh model
    print("Training model on full dataset...")
    data_csv = BACKEND_DIR / 'data' / 'processed' / 'sector_risk_dataset.csv'
    
    model = TariffRiskNN()
    model.train(str(data_csv), epochs=120, batch_size=16, validation_split=0.2)
    
    print()
    
    # Load training data
    df = pd.read_csv(data_csv)
    
    feature_cols = ['exposure_us', 'exposure_cn', 'exposure_mx', 
                   'hhi_concentration', 'export_value', 'top_partner_share']
    
    print(f"Evaluating on {len(df)} training samples...\n")
    
    # Get predictions for all rows
    predictions = []
    actual = []
    
    for _, row in df.iterrows():
        features = {col: row[col] for col in feature_cols}
        pred = model.predict(features)
        predictions.append(pred)
        actual.append(row['risk_score'])
    
    predictions = np.array(predictions)
    actual = np.array(actual)
    
    # Calculate metrics
    mae = mean_absolute_error(actual, predictions)
    rmse = np.sqrt(mean_squared_error(actual, predictions))
    r2 = r2_score(actual, predictions)
    
    # Accuracy within thresholds
    errors = np.abs(actual - predictions)
    within_1 = np.mean(errors <= 1) * 100
    within_2 = np.mean(errors <= 2) * 100
    within_5 = np.mean(errors <= 5) * 100
    within_10 = np.mean(errors <= 10) * 100
    
    print("📊 TRAINING SET PERFORMANCE:")
    print("-" * 70)
    print(f"  Mean Absolute Error (MAE):       {mae:.3f} points")
    print(f"  Root Mean Square Error (RMSE):   {rmse:.3f} points")
    print(f"  R² Score:                        {r2:.4f}")
    print()
    print("  🎯 Prediction Accuracy:")
    print(f"     • Within ±1 point:   {within_1:.1f}%")
    print(f"     • Within ±2 points:  {within_2:.1f}%")
    print(f"     • Within ±5 points:  {within_5:.1f}%")
    print(f"     • Within ±10 points: {within_10:.1f}%")
    print()
    
    # Show some examples
    print("  📋 Sample Predictions (first 10 sectors):")
    print("-" * 70)
    print(f"{'Sector':<40} {'Actual':<10} {'Predicted':<10} {'Error':<10}")
    print("-" * 70)
    
    for i in range(min(10, len(df))):
        sector = df.iloc[i].get('sector_name', f"Sector {i+1}")
        error = abs(actual[i] - predictions[i])
        print(f"{sector:<40} {actual[i]:<10.2f} {predictions[i]:<10.2f} {error:<10.2f}")
    
    print("-" * 70)
    print()
    
    # Interpretation
    if r2 >= 0.99:
        print("✅ EXCELLENT: Near-perfect fit (R² ≥ 0.99)")
    elif r2 >= 0.90:
        print("✅ EXCELLENT: Very strong fit (R² ≥ 0.90) - great for hackathon!")
    elif r2 >= 0.80:
        print("✅ GREAT: Strong model fit (R² ≥ 0.80)")
    elif r2 >= 0.70:
        print("✅ GOOD: Solid model fit (R² ≥ 0.70)")
    else:
        print(f"⚠️  Moderate fit (R² = {r2:.3f})")
    
    print()
    print("="*70)
    print()

if __name__ == '__main__':
    sys.exit(main())
