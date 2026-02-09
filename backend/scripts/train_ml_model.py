#!/usr/bin/env python
"""
Train ML model for TradeRisk
==============================
Trains neural network on sector risk data.

Usage:
    python train_ml_model.py
    
This will:
1. Load sector_risk_dataset.csv
2. Train a neural network to predict risk scores
3. Save the model to backend/models/tariff_risk_nn/
"""

import sys
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Add backend to path
BACKEND_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from src.ml_model import TariffRiskNN


def main():
    """Train and save the ML model."""
    
    print("=" * 70)
    print("TariffShock ML Model Training")
    print("=" * 70)
    print()
    
    # Paths
    data_csv = BACKEND_DIR / 'data' / 'processed' / 'sector_risk_dataset.csv'
    model_dir = BACKEND_DIR / 'models' / 'tariff_risk_nn'
    
    # Check data exists
    if not data_csv.exists():
        print(f"ERROR: Data file not found: {data_csv}")
        print("Please ensure sector_risk_dataset.csv exists.")
        sys.exit(1)
    
    print(f"Data file: {data_csv}")
    print(f"Model output: {model_dir}")
    print()
    
    try:
        # Create and train model
        print("Initializing model...")
        model = TariffRiskNN()
        
        # Load data to check sample count
        import pandas as pd
        df = pd.read_csv(data_csv)
        num_sectors = len(df)
        
        print(f"Training model on {num_sectors} Canadian sectors...")
        print("(This may take 1-2 minutes...)")
        print()
        
        history = model.train(
            str(data_csv),
            epochs=120,
            batch_size=16,
            validation_split=0.2
        )
        
        print()
        print("Training complete!")
        print()
        
        # Save model
        print("Saving model...")
        model.save_model(str(model_dir))
        
        print()
        print("=" * 70)
        print("✅ Model trained and saved successfully!")
        print("=" * 70)
        print()
        print("Model is now available for inference via:")
        print("  - POST /api/predict-ml")
        print("  - POST /api/predict-ml-batch")
        print()
        print("To test:")
        print("  curl -X POST http://localhost:5001/api/predict-ml \\")
        print("    -H 'Content-Type: application/json' \\")
        print("    -d '{")
        print("      \"exposure_us\": 0.95,")
        print("      \"exposure_cn\": 0.01,")
        print("      \"exposure_mx\": 0.0,")
        print("      \"hhi_concentration\": 0.92,")
        print("      \"export_value\": 50000000000,")
        print("      \"top_partner_share\": 0.95")
        print("    }'")
        print()
        
        return 0
        
    except ImportError as e:
        print()
        print("ERROR: TensorFlow and scikit-learn are required")
        print()
        print("Install them with:")
        print("  pip install tensorflow scikit-learn")
        print()
        return 1
        
    except Exception as e:
        print()
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
