"""
TradeRisk API Routes
======================
HTTP API endpoints for the Risk Engine.

Uses Flask for HTTP routing.
"""

from flask import Flask, request, jsonify, Response
from typing import Optional
import logging
import gzip
import json

from .schemas import Partner, ScenarioInput
from .risk_engine import RiskEngine, create_risk_engine
from .load_data import load_data, get_data_loader
from .ml_model import TariffRiskNN
from .routes_backboard import register_backboard_routes
from .routes_gemini import register_gemini_routes

logger = logging.getLogger(__name__)

from flask_cors import CORS


def gzip_response(data):
    """Helper to create gzipped JSON response for large payloads."""
    content = json.dumps(data).encode('utf-8')
    
    # Only compress if larger than 1KB
    if len(content) > 1024:
        gzip_buffer = gzip.compress(content)
        response = Response(gzip_buffer, mimetype='application/json')
        response.headers['Content-Encoding'] = 'gzip'
        response.headers['Vary'] = 'Accept-Encoding'
        return response
    else:
        return jsonify(data)


def create_app(data_dir: Optional[str] = None) -> Flask:
    """
    Create and configure the Flask application.
    
    Args:
        data_dir: Optional path to data directory
        
    Returns:
        Configured Flask application
    """
    app = Flask(__name__)
    CORS(app, resources={r"/api/*": {"origins": "*"}})
    
    # Load data at startup
    try:
        from pathlib import Path
        data_path = Path(data_dir) if data_dir else None
        loader = load_data(data_path)
        engine = create_risk_engine(loader)
        app.config['RISK_ENGINE'] = engine
        logger.info("Risk engine initialized successfully")
        
        # Try to load ML model if available
        try:
            ml_model_path = Path(__file__).parent.parent / 'models' / 'tariff_risk_nn'
            if ml_model_path.exists():
                ml_model = TariffRiskNN(str(ml_model_path))
                app.config['ML_MODEL'] = ml_model
                logger.info("ML model loaded successfully")
            else:
                logger.warning("ML model not found at default path - will use formula-based predictions")
                app.config['ML_MODEL'] = None
        except Exception as e:
            logger.warning(f"Failed to load ML model: {e} - falling back to formula")
            app.config['ML_MODEL'] = None
            
    except Exception as e:
        logger.error(f"Failed to initialize risk engine: {e}")
        raise
    
    # --------------------------------------------------------
    # ROUTES
    # --------------------------------------------------------
    
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint."""
        return jsonify({
            "status": "healthy",
            "engine_loaded": app.config.get('RISK_ENGINE') is not None
        })
    
    @app.route('/api/sectors', methods=['GET'])
    def list_sectors():
        """
        List all available sectors.
        
        Returns:
            JSON array of sector IDs and names
        """
        engine: RiskEngine = app.config['RISK_ENGINE']
        sectors = engine.data_loader.sector_summaries
        
        result = [
            {
                "sector_id": s.sector_id,
                "sector_name": s.sector_name,
                "total_exports": s.total_exports,
                "top_partner": s.top_partner.value,
                "top_partner_share": s.top_partner_share
            }
            for s in sectors.values()
        ]
        
        return jsonify({
            "count": len(result),
            "sectors": result
        })
    
    @app.route('/api/sector/<sector_id>', methods=['GET'])
    def get_sector(sector_id: str):
        """
        Get details for a specific sector.
        
        Args:
            sector_id: Sector ID (HS2 code)
            
        Returns:
            Sector details including partner shares
        """
        engine: RiskEngine = app.config['RISK_ENGINE']
        sector = engine.data_loader.get_sector(sector_id)
        
        if sector is None:
            return jsonify({"error": f"Sector not found: {sector_id}"}), 404
        
        return jsonify({
            "sector_id": sector.sector_id,
            "sector_name": sector.sector_name,
            "total_exports": sector.total_exports,
            "partner_shares": sector.partner_shares,
            "top_partner": sector.top_partner.value,
            "top_partner_share": sector.top_partner_share
        })
    
    @app.route('/api/baseline', methods=['GET'])
    def get_baseline():
        """
        Get baseline risk scores (tariff_percent = 0).
        
        Query params:
            sectors: Comma-separated list of sector IDs (optional)
            
        Returns:
            Risk engine response with baseline values
        """
        engine: RiskEngine = app.config['RISK_ENGINE']
        
        # Parse sector filter
        sector_filter = None
        sectors_param = request.args.get('sectors')
        if sectors_param:
            sector_filter = [s.strip() for s in sectors_param.split(',')]
        
        response = engine.get_baseline(sector_filter)
        return jsonify(response.to_dict())
    
    @app.route('/api/scenario', methods=['POST'])
    def calculate_scenario():
        """
        Calculate risk for a given scenario.
        
        Request body (JSON):
            {
                "tariff_percent": 10,           # 0-25, required
                "target_partners": ["US"],       # Array of: US, China, EU. Required
                "sector_filter": ["01", "02"]    # Optional
            }
            
        Returns:
            Risk engine response with ranked sectors
        """
        engine: RiskEngine = app.config['RISK_ENGINE']
        
        # Parse request body
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Validate tariff_percent
        tariff_percent = data.get('tariff_percent')
        if tariff_percent is None:
            return jsonify({"error": "tariff_percent is required"}), 400
        
        try:
            tariff_percent = float(tariff_percent)
        except (ValueError, TypeError):
            return jsonify({"error": "tariff_percent must be a number"}), 400
        
        if not 0 <= tariff_percent <= 25:
            return jsonify({
                "error": f"tariff_percent must be in range [0, 25], got {tariff_percent}"
            }), 400
        
        # Validate target_partners
        target_partners_raw = data.get('target_partners', [])
        if not isinstance(target_partners_raw, list):
            return jsonify({"error": "target_partners must be an array"}), 400
        
        valid_partners = {"US", "China", "EU"}
        target_partners = []
        for p in target_partners_raw:
            if p not in valid_partners:
                return jsonify({
                    "error": f"Invalid partner: {p}. Valid options: {valid_partners}"
                }), 400
            target_partners.append(Partner(p))
        
        # Parse optional sector_filter
        sector_filter = data.get('sector_filter')
        if sector_filter is not None and not isinstance(sector_filter, list):
            return jsonify({"error": "sector_filter must be an array"}), 400
        
        # Create scenario and calculate
        try:
            scenario = ScenarioInput(
                tariff_percent=tariff_percent,
                target_partners=target_partners,
                sector_filter=sector_filter
            )
            response = engine.calculate_scenario(scenario)
            
            # Use gzip compression for large responses
            return gzip_response(response.to_dict())
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("Error calculating scenario")
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route('/api/compare', methods=['POST'])
    def compare_scenarios():
        """
        Compare two scenarios side by side.
        
        Request body (JSON):
            {
                "baseline": {
                    "tariff_percent": 0,
                    "target_partners": []
                },
                "scenario": {
                    "tariff_percent": 10,
                    "target_partners": ["US"]
                },
                "sector_filter": ["01", "02"]  # Optional
            }
            
        Returns:
            Comparison of baseline vs scenario
        """
        engine: RiskEngine = app.config['RISK_ENGINE']
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400
        
        # Parse baseline
        baseline_data = data.get('baseline', {"tariff_percent": 0, "target_partners": []})
        scenario_data = data.get('scenario')
        
        if not scenario_data:
            return jsonify({"error": "scenario is required"}), 400
        
        sector_filter = data.get('sector_filter')
        
        try:
            # Calculate baseline
            baseline_scenario = ScenarioInput(
                tariff_percent=baseline_data.get('tariff_percent', 0),
                target_partners=[Partner(p) for p in baseline_data.get('target_partners', [])],
                sector_filter=sector_filter
            )
            baseline_response = engine.calculate_scenario(baseline_scenario)
            
            # Calculate scenario
            shock_scenario = ScenarioInput(
                tariff_percent=scenario_data.get('tariff_percent', 0),
                target_partners=[Partner(p) for p in scenario_data.get('target_partners', [])],
                sector_filter=sector_filter
            )
            scenario_response = engine.calculate_scenario(shock_scenario)
            
            # Build comparison
            baseline_dict = {s.sector_id: s for s in baseline_response.sectors}
            
            comparison = []
            for sector in scenario_response.sectors:
                baseline_sector = baseline_dict.get(sector.sector_id)
                baseline_risk = baseline_sector.risk_score if baseline_sector else 0
                
                comparison.append({
                    "sector_id": sector.sector_id,
                    "sector_name": sector.sector_name,
                    "baseline_risk": baseline_risk,
                    "scenario_risk": sector.risk_score,
                    "risk_change": round(sector.risk_score - baseline_risk, 1),
                    "affected_export_value": sector.affected_export_value,
                    "top_partner": sector.top_partner,
                    "dependency_percent": sector.dependency_percent
                })
            
            # Sort by risk_change descending
            comparison.sort(key=lambda x: -x['risk_change'])
            
            return jsonify({
                "baseline_scenario": baseline_data,
                "shock_scenario": scenario_data,
                "comparison": comparison,
                "biggest_gainers": comparison[:5],
                "total_sectors": len(comparison)
            })
            
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        except Exception as e:
            logger.exception("Error comparing scenarios")
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route('/api/actual-tariffs', methods=['GET'])
    def get_actual_tariffs_on_canada():
        """
        Get risk calculated using ACTUAL tariff rates on Canada.
        
        This uses real tariff data including:
        - Section 232 steel/aluminum tariffs (25%/10%)
        - Softwood lumber duties (~20%)
        - Various agricultural tariffs
        
        Query params:
            partners: Comma-separated list of partners (default: US)
            sectors: Comma-separated list of sector IDs (optional)
            
        Returns:
            Risk engine response with actual tariff impacts
        """
        engine: RiskEngine = app.config['RISK_ENGINE']
        
        # Parse partners
        partners_param = request.args.get('partners', 'US')
        valid_partners = {"US", "China", "EU"}
        target_partners = []
        
        for p in partners_param.split(','):
            p = p.strip()
            if p in valid_partners:
                target_partners.append(Partner(p))
        
        if not target_partners:
            target_partners = [Partner.US]
        
        # Parse sector filter
        sector_filter = None
        sectors_param = request.args.get('sectors')
        if sectors_param:
            sector_filter = [s.strip() for s in sectors_param.split(',')]
        
        try:
            response = engine.calculate_actual_tariffs_on_canada(
                target_partners=target_partners,
                sector_filter=sector_filter
            )
            return jsonify(response.to_dict())
        except Exception as e:
            logger.exception("Error calculating actual tariff impact")
            return jsonify({"error": "Internal server error"}), 500
    
    @app.route('/api/tariff-rates', methods=['GET'])
    def get_tariff_rates():
        """
        Get the actual tariff rates on Canadian exports by sector.
        
        Returns:
            Dictionary of HS2 codes to tariff rates by partner
        """
        from .tariff_data import get_all_tariffed_sectors, US_TARIFFS_ON_CANADA
        
        all_tariffs = get_all_tariffed_sectors()
        engine: RiskEngine = app.config['RISK_ENGINE']
        
        # Add sector names
        result = []
        for hs2, rates in all_tariffs.items():
            sector = engine.data_loader.get_sector(hs2)
            result.append({
                "hs2": hs2,
                "sector_name": sector.sector_name if sector else f"Sector {hs2}",
                "tariff_rates": rates,
                "max_tariff": max(rates.values())
            })
        
        # Sort by max tariff
        result.sort(key=lambda x: -x['max_tariff'])
        
        return jsonify({
            "description": "Actual tariff rates imposed on Canadian exports",
            "note": "Includes Section 232 steel/aluminum, softwood lumber, and other duties",
            "tariffs": result,
            "total_tariffed_sectors": len(result)
        })
    
    @app.route('/api/partners', methods=['GET'])
    def list_partners():
        """List valid trading partners."""
        return jsonify({
            "partners": [
                {"id": "US", "name": "United States"},
                {"id": "China", "name": "China"},
                {"id": "EU", "name": "European Union"}
            ],
            "note": "All other countries are aggregated as 'Other'"
        })
    
    @app.route('/api/config', methods=['GET'])
    def get_config():
        """Get risk engine configuration."""
        from .risk_engine import W_EXPOSURE, W_CONCENTRATION, MAX_TARIFF_PERCENT
        
        ml_model = app.config.get('ML_MODEL')
        
        return jsonify({
            "w_exposure": W_EXPOSURE,
            "w_concentration": W_CONCENTRATION,
            "max_tariff_percent": MAX_TARIFF_PERCENT,
            "risk_formula": "risk = (w_exposure * exposure + w_concentration * concentration) * shock",
            "shock_formula": "shock = tariff_percent / 25",
            "ml_model_available": ml_model is not None,
            "ml_model_note": "ML model provides more accurate predictions based on neural network training"
        })
    
    @app.route('/api/predict-ml', methods=['POST'])
    def predict_ml_risk():
        """
        Predict tariff impact risk using trained neural network.
        More accurate than formula-based approach.
        
        Expected JSON:
        {
            "tariff_percent": float (0-25),
            "exposure_us": float (0-1),
            "exposure_cn": float (0-1),
            "exposure_mx": float (0-1),
            "hhi_concentration": float (0-1),
            "export_value": float (dollars),
            "top_partner_share": float (0-1)
        }
        
        Returns:
            Predicted risk score (0-100)
        """
        ml_model = app.config.get('ML_MODEL')
        
        if ml_model is None:
            return jsonify({
                "error": "ML model not loaded",
                "note": "Train and save the model first using scripts/train_ml_model.py"
            }), 503
        
        try:
            data = request.get_json()
            
            if not data:
                return jsonify({"error": "No JSON payload provided"}), 400
            
            # Predict
            pred_risk = ml_model.predict(data)
            
            return jsonify({
                "method": "neural_network",
                "predicted_risk_score": round(pred_risk, 2),
                "features_used": list(data.keys()),
                "confidence": "High - trained on 98 Canadian sectors"
            })
            
        except Exception as e:
            logger.error(f"ML prediction error: {e}")
            return jsonify({"error": str(e)}), 400
    
    @app.route('/api/predict-ml-batch', methods=['POST'])
    def predict_ml_batch():
        """
        Predict tariff impact risk for multiple sectors using ML.
        
        Expected JSON:
        {
            "sectors": [
                {"sector_id": "87", "export_value": 50000000000, ...},
                ...
            ]
        }
        
        Returns:
            List of predictions
        """
        ml_model = app.config.get('ML_MODEL')
        
        if ml_model is None:
            return jsonify({
                "error": "ML model not loaded"
            }), 503
        
        try:
            data = request.get_json()
            sectors = data.get('sectors', [])
            
            if not sectors:
                return jsonify({"error": "No sectors provided"}), 400
            
            engine: RiskEngine = app.config['RISK_ENGINE']
            tariff_percent = data.get('tariff_percent', 10.0)
            
            results = []
            for sector_id in sectors:
                sector = engine.data_loader.get_sector(sector_id)
                if sector:
                    features = {
                        'tariff_percent': tariff_percent,
                        'exposure_us': sector.partner_shares.get('US', 0),
                        'exposure_cn': sector.partner_shares.get('China', 0),
                        'exposure_mx': sector.partner_shares.get('Mexico', 0),
                        'hhi_concentration': sector.top_partner_share,
                        'export_value': sector.total_exports,
                        'top_partner_share': sector.top_partner_share
                    }
                    pred = ml_model.predict(features)
                    results.append({
                        "sector_id": sector_id,
                        "sector_name": sector.sector_name,
                        "ml_predicted_risk": round(pred, 2)
                    })
            
            return jsonify({
                "method": "neural_network",
                "count": len(results),
                "predictions": results
            })
            
        except Exception as e:
            logger.error(f"ML batch prediction error: {e}")
            return jsonify({"error": str(e)}), 400
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404
    
    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error"}), 500
    
    register_backboard_routes(app)
    register_gemini_routes(app)
    
    return app


# For running directly
if __name__ == '__main__':
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    data_dir = sys.argv[1] if len(sys.argv) > 1 else None
    app = create_app(data_dir)
    app.run(host='0.0.0.0', port=5001, debug=True)
