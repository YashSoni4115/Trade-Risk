# Trade-Risk

https://github.com/user-attachments/assets/27ca206f-38a5-49af-99aa-4eeb23480c03

Trade-Risk is a tariff risk engine that quantifies how changes in trade policy impact Canadian export sectors. It enables scenario based stress testing, baseline comparisons, and AI generated explanations for policy and risk analysis.

The system combines an explainable deterministic economic risk model with an optional machine learning model trained on real Canadian trade data. Risk scores reflect sector exposure, partner concentration, and tariff shock magnitude.

To support scalable and consistent AI explanations, Trade-Risk uses Backboard as a caching layer between the risk engine and Gemini. Scenario level results and explanations are stored and reused to ensure deterministic outputs, reduce repeated Gemini calls, and enable versioned, auditable explanations.

## Technologies Used

- Python and Flask (API)
- Deterministic economic risk modeling
- Neural network (TensorFlow / Keras)
- pandas and NumPy for data processing
- Backboard.io for AI memory and caching
- Gemini API for natural language explanations
- pytest for automated testing

Built for CxC 2026.
