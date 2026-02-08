"""
Backboard Data Layer
====================
Maps TariffShock outputs to Backboard.io documents and provides caching policy.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from .schemas import Partner, ScenarioInput, SectorRiskOutput
from .risk_engine import RiskEngine
from .ml_model import TariffRiskNN
from .backboard_client import BackboardClient, BackboardError
from .config import ENGINE_VERSION

logger = logging.getLogger(__name__)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"))


def scenario_hash(
    tariff_percent: float,
    target_partners: List[str],
    sector_filter: Optional[List[str]],
    model_mode: str,
) -> str:
    normalized = normalize_scenario_inputs(
        tariff_percent=tariff_percent,
        target_partners=target_partners,
        sector_filter=sector_filter,
        model_mode=model_mode,
    )
    canonical = _canonical_json(normalized)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def normalize_scenario_inputs(
    tariff_percent: float,
    target_partners: List[str],
    sector_filter: Optional[List[str]],
    model_mode: str,
) -> Dict[str, Any]:
    tariff_normalized = round(float(tariff_percent), 2)
    partners_normalized = sorted({str(p) for p in target_partners})
    if sector_filter:
        sector_normalized = sorted({str(s).zfill(2) for s in sector_filter})
    else:
        sector_normalized = []
    mode_normalized = str(model_mode or "deterministic").lower()
    return {
        "tariff_percent": tariff_normalized,
        "target_partners": partners_normalized,
        "sector_filter": sector_normalized,
        "model_mode": mode_normalized,
    }


@dataclass
class CachedResult:
    scenario: Dict[str, Any]
    risk_result: Dict[str, Any]


class BackboardDataLayer:
    """Coordinates Backboard caching with TariffShock computation."""

    def __init__(
        self,
        client: BackboardClient,
        risk_engine: RiskEngine,
        ml_model: Optional[TariffRiskNN],
        engine_version: str = ENGINE_VERSION,
    ) -> None:
        self.client = client
        self.risk_engine = risk_engine
        self.ml_model = ml_model
        self.engine_version = engine_version

    def _result_id(self, scenario_id: str, model_mode: str) -> str:
        return f"{scenario_id}:{model_mode}"

    def get_cached_result(self, scenario_id: str, model_mode: str) -> Optional[CachedResult]:
        scenario = self.client.get("scenarios", scenario_id)
        if not scenario or scenario.get("engine_version") != self.engine_version:
            return None

        result_id = self._result_id(scenario_id, model_mode)
        risk_result = self.client.get("risk_results", result_id)
        if not risk_result or risk_result.get("engine_version") != self.engine_version:
            return None

        return CachedResult(scenario=scenario, risk_result=risk_result)

    def upsert_sector(self, sector: Dict[str, Any]) -> None:
        sector_id = sector["sector_id"]
        payload = {**sector, "updated_at": _utc_now()}
        self.client.upsert("sectors", sector_id, payload)

    def upsert_scenario(self, scenario_id: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "scenario_id": scenario_id,
            "created_at": _utc_now(),
            "inputs": inputs,
            "engine_version": self.engine_version,
        }
        self.client.upsert("scenarios", scenario_id, payload)
        return payload

    def upsert_risk_result(self, scenario_id: str, model_mode: str, risk_result: Dict[str, Any]) -> Dict[str, Any]:
        result_id = self._result_id(scenario_id, model_mode)
        payload = {
            "result_id": result_id,
            "scenario_id": scenario_id,
            "model_mode": model_mode,
            "created_at": _utc_now(),
            **risk_result,
            "engine_version": self.engine_version,
        }
        self.client.upsert("risk_results", result_id, payload)
        return payload

    def get_existing_explanation(
        self,
        scenario_id: str,
        sector_id: str,
        explanation_type: str,
    ) -> Optional[Dict[str, Any]]:
        explanation_id = f"{scenario_id}:{sector_id}:{explanation_type}"
        return self.client.get("explanations", explanation_id)

    def upsert_explanation(
        self,
        scenario_id: str,
        sector_id: str,
        explanation_type: str,
        content: str,
        grounded_metrics: Dict[str, Any],
        model: str,
        safety: Dict[str, Any],
    ) -> Dict[str, Any]:
        explanation_id = f"{scenario_id}:{sector_id}:{explanation_type}"
        payload = {
            "explanation_id": explanation_id,
            "scenario_id": scenario_id,
            "sector_id": sector_id,
            "type": explanation_type,
            "content": content,
            "grounded_metrics": grounded_metrics,
            "created_at": _utc_now(),
            "model": model,
            "safety": safety,
        }
        self.client.upsert("explanations", explanation_id, payload)
        return payload

    def _deterministic_results(self, scenario_input: ScenarioInput) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], Dict[str, SectorRiskOutput]]:
        baseline = self.risk_engine.get_baseline(scenario_input.sector_filter)
        scenario = self.risk_engine.calculate_scenario(scenario_input)

        baseline_rows = [s.to_dict() for s in baseline.sectors]
        scenario_rows = [s.to_dict() for s in scenario.sectors]
        by_id = {s.sector_id: s for s in scenario.sectors}
        return baseline_rows, scenario_rows, by_id

    def _ml_results(
        self,
        scenario_input: ScenarioInput,
        deterministic_by_id: Dict[str, SectorRiskOutput],
    ) -> List[Dict[str, Any]]:
        if self.ml_model is None:
            return []

        scenario_rows: List[Dict[str, Any]] = []
        for sector_id, deterministic in deterministic_by_id.items():
            sector = self.risk_engine.data_loader.get_sector(sector_id)
            if not sector:
                continue

            features = {
                "exposure_us": sector.partner_shares.get("US", 0),
                "exposure_cn": sector.partner_shares.get("China", 0),
                "exposure_mx": sector.partner_shares.get("Mexico", 0),
                "hhi_concentration": sector.top_partner_share,
                "export_value": sector.total_exports,
                "top_partner_share": sector.top_partner_share,
            }
            ml_score = float(self.ml_model.predict(features))
            row = deterministic.to_dict()
            row["risk_score"] = round(ml_score, 1)
            row["risk_delta"] = round(ml_score, 1)
            row["ml_predicted_risk"] = round(ml_score, 2)
            scenario_rows.append(row)

        scenario_rows.sort(key=lambda x: (-x["risk_score"], -x["risk_delta"]))
        return scenario_rows

    def compute_risk_result(self, scenario_input: ScenarioInput, model_mode: str) -> Dict[str, Any]:
        baseline_rows, deterministic_rows, deterministic_by_id = self._deterministic_results(scenario_input)

        if model_mode == "deterministic" or self.ml_model is None:
            scenario_rows = deterministic_rows
        else:
            scenario_rows = self._ml_results(scenario_input, deterministic_by_id)
            if not scenario_rows:
                scenario_rows = deterministic_rows

        biggest_movers = sorted(scenario_rows, key=lambda x: abs(x.get("risk_delta", 0)), reverse=True)[:5]
        top_risk_sectors = sorted(scenario_rows, key=lambda x: x.get("risk_score", 0), reverse=True)[:5]
        affected_export_total = round(sum(r.get("affected_export_value", 0) for r in scenario_rows), 2)

        explainability = {
            sector_id: {
                "exposure": det.explainability.exposure_value,
                "concentration": det.explainability.concentration_value,
                "shock": det.explainability.shock_value,
            }
            for sector_id, det in deterministic_by_id.items()
        }

        result = {
            "baseline": {"risk_scores": baseline_rows},
            "scenario": {"risk_scores": scenario_rows},
            "summary": {
                "biggest_movers": biggest_movers,
                "top_risk_sectors": top_risk_sectors,
                "affected_export_total": affected_export_total,
            },
            "explainability": {"per_sector_drivers": explainability},
        }

        if model_mode == "both":
            result["summary"]["deterministic_top_risk_sectors"] = top_risk_sectors

        return result

    def build_chat_context(
        self,
        scenario_input: ScenarioInput,
        sector_id: str,
        model_mode: str,
        explanation_type: str,
        cached: bool,
        risk_result: Dict[str, Any],
        scenario_doc: Dict[str, Any],
        existing_explanation: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        scenario_rows = risk_result["scenario"]["risk_scores"]
        baseline_rows = risk_result["baseline"]["risk_scores"]

        scenario_row = next((r for r in scenario_rows if r.get("sector_id") == sector_id), None)
        baseline_row = next((r for r in baseline_rows if r.get("sector_id") == sector_id), None)

        if scenario_row is None or baseline_row is None:
            raise ValueError(f"Sector not found in risk results: {sector_id}")

        sector = self.risk_engine.data_loader.get_sector(sector_id)
        if sector is None:
            raise ValueError(f"Sector not found: {sector_id}")

        drivers = [
            {"name": "Exposure", "value": scenario_row.get("exposure")},
            {"name": "Concentration", "value": scenario_row.get("concentration")},
            {"name": "Shock", "value": scenario_row.get("shock")},
        ]

        leaderboard = [
            {
                "sector_id": row.get("sector_id"),
                "sector_name": row.get("sector_name"),
                "risk_score": row.get("risk_score"),
                "delta": row.get("risk_delta"),
            }
            for row in risk_result["summary"]["top_risk_sectors"]
        ][:5]

        return {
            "scenario": {
                **scenario_doc.get("inputs", {}),
                "scenario_id": scenario_doc.get("scenario_id"),
                "engine_version": scenario_doc.get("engine_version"),
            },
            "sector": {
                "sector_id": sector.sector_id,
                "sector_name": sector.sector_name,
                "top_partner": sector.top_partner.value,
                "top_partner_share": sector.top_partner_share,
                "partner_shares": sector.partner_shares,
            },
            "risk": {
                "baseline_risk": baseline_row.get("risk_score"),
                "scenario_risk": scenario_row.get("risk_score"),
                "delta": round(scenario_row.get("risk_score", 0) - baseline_row.get("risk_score", 0), 1),
                "exposure": scenario_row.get("exposure"),
                "concentration": scenario_row.get("concentration"),
                "shock": scenario_row.get("shock"),
                "affected_export_value": scenario_row.get("affected_export_value"),
            },
            "drivers": drivers,
            "leaderboard_snippet": leaderboard,
            "cached": cached,
            "existing_explanation": existing_explanation.get("content") if existing_explanation else None,
        }

    def get_or_compute_chat_context(
        self,
        tariff_percent: float,
        target_partners: List[str],
        sector_id: str,
        model_mode: str,
        explanation_type: str,
        sector_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        normalized = normalize_scenario_inputs(
            tariff_percent=tariff_percent,
            target_partners=target_partners,
            sector_filter=sector_filter,
            model_mode=model_mode,
        )
        scenario_id = scenario_hash(**normalized)
        backboard_unavailable = False
        try:
            cached = self.get_cached_result(scenario_id, normalized["model_mode"])
        except BackboardError:
            cached = None
            backboard_unavailable = True

        scenario_doc: Dict[str, Any]
        risk_result: Dict[str, Any]
        cached_hit = False

        if cached:
            scenario_doc = cached.scenario
            risk_result = cached.risk_result
            cached_hit = True
        else:
            scenario_input = ScenarioInput(
                tariff_percent=normalized["tariff_percent"],
                target_partners=[Partner(p) for p in normalized["target_partners"]],
                sector_filter=normalized["sector_filter"],
            )
            risk_result = self.compute_risk_result(scenario_input, normalized["model_mode"])
            scenario_doc = {
                "scenario_id": scenario_id,
                "inputs": normalized,
                "engine_version": self.engine_version,
            }

            try:
                scenario_doc = self.upsert_scenario(scenario_id, normalized)
                self.upsert_risk_result(scenario_id, normalized["model_mode"], risk_result)

                for row in risk_result["scenario"]["risk_scores"]:
                    sector_obj = self.risk_engine.data_loader.get_sector(row.get("sector_id"))
                    if sector_obj is None:
                        continue
                    sector_payload = {
                        "sector_id": sector_obj.sector_id,
                        "sector_name": sector_obj.sector_name,
                        "total_exports": sector_obj.total_exports,
                        "partner_shares": sector_obj.partner_shares,
                        "top_partner": sector_obj.top_partner.value,
                        "top_partner_share": sector_obj.top_partner_share,
                    }
                    self.upsert_sector(sector_payload)
            except BackboardError:
                backboard_unavailable = True

        existing_explanation = None
        try:
            existing_explanation = self.get_existing_explanation(scenario_id, sector_id, explanation_type)
        except BackboardError:
            existing_explanation = None
            backboard_unavailable = True

        scenario_input = ScenarioInput(
            tariff_percent=normalized["tariff_percent"],
            target_partners=[Partner(p) for p in normalized["target_partners"]],
            sector_filter=normalized["sector_filter"],
        )

        context = self.build_chat_context(
            scenario_input=scenario_input,
            sector_id=sector_id,
            model_mode=normalized["model_mode"],
            explanation_type=explanation_type,
            cached=cached_hit,
            risk_result=risk_result,
            scenario_doc=scenario_doc,
            existing_explanation=existing_explanation,
        )
        if backboard_unavailable and not cached_hit:
            context["warning"] = "Backboard unavailable; computed locally"
            context["cached"] = False
        return context
