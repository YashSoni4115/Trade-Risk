"""
Backboard API Routes
====================
Chatbot-facing endpoints that read/write via Backboard.io.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from flask import Flask, jsonify, request, current_app

from .backboard_client import BackboardClient, BackboardError
from .data_layer import BackboardDataLayer
from .config import ENGINE_VERSION

logger = logging.getLogger(__name__)


def _get_data_layer(app: Flask) -> BackboardDataLayer:
    layer = app.config.get("BACKBOARD_DATA_LAYER")
    if layer is None:
        client = BackboardClient()
        layer = BackboardDataLayer(
            client=client,
            risk_engine=app.config["RISK_ENGINE"],
            ml_model=app.config.get("ML_MODEL"),
            engine_version=ENGINE_VERSION,
        )
        app.config["BACKBOARD_DATA_LAYER"] = layer
    return layer


def register_backboard_routes(app: Flask) -> None:
    """Register Backboard-related routes on the Flask app."""

    @app.route("/api/chat/context", methods=["POST"])
    def chat_context() -> Any:
        data = request.get_json() or {}

        required = ["tariff_percent", "target_partners", "sector_id"]
        missing = [key for key in required if key not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        model_mode = data.get("model_mode", "deterministic")
        explanation_type = data.get("explanation_type", "explanation")
        sector_filter = data.get("sector_filter")

        layer = _get_data_layer(current_app)

        try:
            context = layer.get_or_compute_chat_context(
                tariff_percent=data["tariff_percent"],
                target_partners=data["target_partners"],
                sector_id=str(data["sector_id"]).zfill(2),
                model_mode=model_mode,
                explanation_type=explanation_type,
                sector_filter=sector_filter,
            )
            return jsonify(context)
        except Exception as exc:
            logger.error(f"Chat context error: {exc}")
            return jsonify({"error": "Failed to compute context"}), 500

    @app.route("/api/chat/explanation", methods=["POST"])
    def store_explanation() -> Any:
        data = request.get_json() or {}
        required = ["scenario_id", "sector_id", "type", "content", "grounded_metrics", "model", "safety"]
        missing = [key for key in required if key not in data]
        if missing:
            return jsonify({"error": f"Missing fields: {', '.join(missing)}"}), 400

        layer = _get_data_layer(current_app)

        try:
            payload = layer.upsert_explanation(
                scenario_id=data["scenario_id"],
                sector_id=str(data["sector_id"]).zfill(2),
                explanation_type=data["type"],
                content=data["content"],
                grounded_metrics=data["grounded_metrics"],
                model=data["model"],
                safety=data["safety"],
            )
            return jsonify(payload)
        except BackboardError as exc:
            logger.error(f"Backboard store explanation error: {exc}")
            return jsonify({"error": "Backboard unavailable"}), 503
        except Exception as exc:
            logger.error(f"Store explanation error: {exc}")
            return jsonify({"error": "Failed to store explanation"}), 500
