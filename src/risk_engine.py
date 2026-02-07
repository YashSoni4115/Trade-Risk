"""
TariffShock Risk Engine
=======================
Deterministic computation module for quantifying tariff exposure risk.

This module:
- Quantifies tariff exposure risk at the sector level
- Recalculates risk scores under simulated tariff scenarios
- Produces numeric, explainable outputs for visualization and AI layers

This module does NOT:
- Fetch external data
- Predict or forecast future trade
- Generate natural language explanations
- Call LLMs or AI APIs
"""

from typing import List, Dict, Optional
import logging

from .schemas import (
    Partner,
    SectorSummary,
    ScenarioInput,
    ExplainabilityOutput,
    SectorRiskOutput,
    RiskEngineResponse
)
from .load_data import DataLoader, get_data_loader
from .tariff_data import get_tariff_rate, get_all_tariffed_sectors, US_TARIFFS_ON_CANADA

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURATION PARAMETERS (FIXED WEIGHTS)
# ============================================================

# Risk calculation weights (must sum to 1)
W_EXPOSURE: float = 0.6
W_CONCENTRATION: float = 0.4

# Shock normalization denominator
MAX_TARIFF_PERCENT: float = 25.0

# Validation
assert W_EXPOSURE + W_CONCENTRATION == 1.0, "Weights must sum to 1"


# ============================================================
# RISK ENGINE CLASS
# ============================================================

class RiskEngine:
    """
    Deterministic risk calculation engine.
    
    Calculates tariff exposure risk for Canadian sectors based on:
    - Exposure to target trading partners
    - Export concentration (dependency on top partner)
    - Tariff shock magnitude
    
    All calculations are deterministic and explainable.
    """
    
    def __init__(self, data_loader: Optional[DataLoader] = None):
        """
        Initialize the risk engine.
        
        Args:
            data_loader: Optional DataLoader instance. If not provided,
                        uses the global data loader.
        """
        self.data_loader = data_loader or get_data_loader()
        self._ensure_data_loaded()
    
    def _ensure_data_loaded(self) -> None:
        """Ensure data is loaded before calculations."""
        if not self.data_loader._is_loaded:
            self.data_loader.load()
    
    def calculate_exposure(
        self, 
        sector: SectorSummary, 
        target_partners: List[Partner]
    ) -> float:
        """
        Calculate exposure to target trading partners.
        
        Exposure = sum of partner shares for all selected target_partners
        
        Args:
            sector: Sector summary data
            target_partners: List of partners to calculate exposure for
            
        Returns:
            Exposure value in range [0, 1]
        """
        if not target_partners:
            return 0.0
        
        exposure = 0.0
        for partner in target_partners:
            partner_key = partner.value  # "US", "China", "EU", "Other"
            exposure += sector.partner_shares.get(partner_key, 0.0)
        
        # Clamp to [0, 1]
        return min(1.0, max(0.0, exposure))
    
    def calculate_concentration(self, sector: SectorSummary) -> float:
        """
        Calculate export concentration.
        
        Concentration = top_partner_share
        
        Args:
            sector: Sector summary data
            
        Returns:
            Concentration value in range [0, 1]
        """
        return sector.top_partner_share
    
    def calculate_shock(self, tariff_percent: float) -> float:
        """
        Calculate normalized shock value.
        
        Shock = tariff_percent / 25
        
        Args:
            tariff_percent: Tariff increase percentage (0-25)
            
        Returns:
            Shock value in range [0, 1]
        """
        return tariff_percent / MAX_TARIFF_PERCENT
    
    def calculate_raw_risk(
        self, 
        exposure: float, 
        concentration: float, 
        shock: float
    ) -> float:
        """
        Calculate raw risk score.
        
        risk_raw = (w_exposure * exposure + w_concentration * concentration) * shock
        
        Args:
            exposure: Exposure value [0, 1]
            concentration: Concentration value [0, 1]
            shock: Shock value [0, 1]
            
        Returns:
            Raw risk score in range [0, 1]
        """
        return (W_EXPOSURE * exposure + W_CONCENTRATION * concentration) * shock
    
    def calculate_risk_score(
        self, 
        exposure: float, 
        concentration: float, 
        shock: float
    ) -> float:
        """
        Calculate normalized risk score (0-100).
        
        risk_score = risk_raw * 100, rounded to 1 decimal place
        
        Args:
            exposure: Exposure value [0, 1]
            concentration: Concentration value [0, 1]
            shock: Shock value [0, 1]
            
        Returns:
            Risk score in range [0, 100], rounded to 1 decimal
        """
        risk_raw = self.calculate_raw_risk(exposure, concentration, shock)
        risk_score = risk_raw * 100
        return round(risk_score, 1)
    
    def calculate_affected_export_value(
        self, 
        total_exports: float, 
        exposure: float, 
        shock: float
    ) -> float:
        """
        Calculate affected export value (proxy).
        
        affected_export_value = total_exports * exposure * shock
        
        Args:
            total_exports: Total export value for sector
            exposure: Exposure value [0, 1]
            shock: Shock value [0, 1]
            
        Returns:
            Affected export value (proxy estimate)
        """
        return total_exports * exposure * shock
    
    def calculate_sector_risk(
        self, 
        sector: SectorSummary, 
        scenario: ScenarioInput,
        use_actual_tariffs: bool = False
    ) -> SectorRiskOutput:
        """
        Calculate complete risk output for a single sector.
        
        Args:
            sector: Sector summary data
            scenario: Scenario input parameters
            use_actual_tariffs: If True, use actual tariff rates on Canada
                               instead of the simulated tariff_percent
            
        Returns:
            Complete risk output for the sector
        """
        # Calculate components
        exposure = self.calculate_exposure(sector, scenario.target_partners)
        concentration = self.calculate_concentration(sector)
        
        # Calculate shock - either from scenario or actual tariffs on Canada
        if use_actual_tariffs:
            # Use actual tariff rates imposed on Canada for this sector
            actual_tariff = self._get_actual_tariff_for_sector(
                sector.sector_id, 
                scenario.target_partners
            )
            shock = self.calculate_shock(actual_tariff)
            effective_tariff = actual_tariff
        else:
            shock = self.calculate_shock(scenario.tariff_percent)
            effective_tariff = scenario.tariff_percent
        
        # Calculate risk score
        risk_score = self.calculate_risk_score(exposure, concentration, shock)
        
        # Baseline risk (tariff_percent = 0 → shock = 0 → baseline_risk = 0)
        baseline_risk = 0.0
        risk_delta = risk_score - baseline_risk
        
        # Affected export value (proxy)
        affected_export_value = self.calculate_affected_export_value(
            sector.total_exports, exposure, shock
        )
        
        # Explainability output
        explainability = ExplainabilityOutput(
            exposure_value=round(exposure, 4),
            concentration_value=round(concentration, 4),
            shock_value=round(shock, 4),
            exposure_component=round(W_EXPOSURE * exposure, 4),
            concentration_component=round(W_CONCENTRATION * concentration, 4)
        )
        
        return SectorRiskOutput(
            sector_id=sector.sector_id,
            sector_name=sector.sector_name,
            risk_score=risk_score,
            risk_delta=round(risk_delta, 1),
            exposure=round(exposure, 4),
            concentration=round(concentration, 4),
            shock=round(shock, 4),
            top_partner=sector.top_partner.value,
            dependency_percent=round(sector.top_partner_share * 100, 1),
            affected_export_value=round(affected_export_value, 2),
            explainability=explainability
        )
    
    def _get_actual_tariff_for_sector(
        self, 
        sector_id: str, 
        target_partners: List[Partner]
    ) -> float:
        """
        Get the actual tariff rate on Canada for a sector from target partners.
        
        Uses the maximum tariff among all target partners.
        
        Args:
            sector_id: HS2 code
            target_partners: List of partners imposing tariffs
            
        Returns:
            Maximum tariff rate (0-25, capped)
        """
        max_tariff = 0.0
        for partner in target_partners:
            tariff = get_tariff_rate(sector_id, partner.value)
            max_tariff = max(max_tariff, tariff)
        
        # Cap at MAX_TARIFF_PERCENT for normalization
        return min(max_tariff, MAX_TARIFF_PERCENT)
    
    def calculate_scenario(self, scenario: ScenarioInput) -> RiskEngineResponse:
        """
        Calculate risk for all sectors under a given scenario.
        
        Args:
            scenario: Scenario input parameters
            
        Returns:
            Complete risk engine response with ranked sectors
        """
        self._ensure_data_loaded()
        
        # Get sectors to process
        all_sectors = self.data_loader.sector_summaries
        
        if scenario.sector_filter:
            sector_ids = [s for s in scenario.sector_filter if s in all_sectors]
        else:
            sector_ids = list(all_sectors.keys())
        
        # Calculate risk for each sector
        results: List[SectorRiskOutput] = []
        for sector_id in sector_ids:
            sector = all_sectors.get(sector_id)
            if sector is None:
                logger.warning(f"Unknown sector_id: {sector_id}, skipping")
                continue
            
            try:
                result = self.calculate_sector_risk(sector, scenario)
                results.append(result)
            except Exception as e:
                logger.error(f"Error calculating risk for sector {sector_id}: {e}")
                continue
        
        # Sort by risk_score (descending), then by risk_delta (descending)
        results.sort(key=lambda x: (-x.risk_score, -x.risk_delta))
        
        # Get biggest movers (top 5 by absolute risk_delta)
        biggest_movers = sorted(
            results, 
            key=lambda x: abs(x.risk_delta), 
            reverse=True
        )[:5]
        
        # Build response
        scenario_dict = {
            "tariff_percent": scenario.tariff_percent,
            "target_partners": [p.value for p in scenario.target_partners],
            "sector_filter": scenario.sector_filter
        }
        
        metadata = {
            "total_sectors": len(results),
            "w_exposure": W_EXPOSURE,
            "w_concentration": W_CONCENTRATION,
            "max_tariff_percent": MAX_TARIFF_PERCENT
        }
        
        return RiskEngineResponse(
            scenario=scenario_dict,
            sectors=results,
            biggest_movers=biggest_movers,
            metadata=metadata
        )
    
    def get_baseline(self, sector_filter: Optional[List[str]] = None) -> RiskEngineResponse:
        """
        Get baseline risk (tariff_percent = 0).
        
        Args:
            sector_filter: Optional list of sector IDs to include
            
        Returns:
            Risk engine response with baseline values
        """
        scenario = ScenarioInput(
            tariff_percent=0,
            target_partners=[],
            sector_filter=sector_filter
        )
        return self.calculate_scenario(scenario)
    
    def calculate_actual_tariffs_on_canada(
        self, 
        target_partners: Optional[List[Partner]] = None,
        sector_filter: Optional[List[str]] = None
    ) -> RiskEngineResponse:
        """
        Calculate risk using ACTUAL tariff rates imposed on Canada.
        
        This uses real tariff data (e.g., Section 232 steel/aluminum tariffs,
        softwood lumber duties, etc.) rather than simulated rates.
        
        Args:
            target_partners: Partners imposing tariffs (default: US)
            sector_filter: Optional list of sector IDs to include
            
        Returns:
            Risk engine response with actual tariff impacts
        """
        self._ensure_data_loaded()
        
        if target_partners is None:
            target_partners = [Partner.US]
        
        # Get sectors to process
        all_sectors = self.data_loader.sector_summaries
        
        if sector_filter:
            sector_ids = [s for s in sector_filter if s in all_sectors]
        else:
            sector_ids = list(all_sectors.keys())
        
        # Calculate risk for each sector using actual tariffs
        results: List[SectorRiskOutput] = []
        for sector_id in sector_ids:
            sector = all_sectors.get(sector_id)
            if sector is None:
                continue
            
            # Get actual tariff rate for this sector
            actual_tariff = self._get_actual_tariff_for_sector(sector_id, target_partners)
            
            # Create a scenario with the actual tariff
            scenario = ScenarioInput(
                tariff_percent=actual_tariff,
                target_partners=target_partners,
                sector_filter=None
            )
            
            try:
                result = self.calculate_sector_risk(sector, scenario, use_actual_tariffs=True)
                results.append(result)
            except Exception as e:
                logger.error(f"Error calculating actual tariff impact for sector {sector_id}: {e}")
                continue
        
        # Sort by risk_score (descending)
        results.sort(key=lambda x: (-x.risk_score, -x.risk_delta))
        
        # Get biggest movers
        biggest_movers = sorted(
            results, 
            key=lambda x: abs(x.risk_delta), 
            reverse=True
        )[:5]
        
        # Build response
        scenario_dict = {
            "mode": "actual_tariffs_on_canada",
            "target_partners": [p.value for p in target_partners],
            "sector_filter": sector_filter,
            "note": "Using actual tariff rates imposed on Canadian exports"
        }
        
        # Include tariff rate info
        tariff_info = {}
        for sector_id in sector_ids:
            tariff = self._get_actual_tariff_for_sector(sector_id, target_partners)
            if tariff > 0:
                sector = all_sectors.get(sector_id)
                if sector:
                    tariff_info[sector_id] = {
                        "sector_name": sector.sector_name,
                        "tariff_rate": tariff
                    }
        
        metadata = {
            "total_sectors": len(results),
            "sectors_with_tariffs": len(tariff_info),
            "w_exposure": W_EXPOSURE,
            "w_concentration": W_CONCENTRATION,
            "max_tariff_percent": MAX_TARIFF_PERCENT,
            "tariff_rates": tariff_info
        }
        
        return RiskEngineResponse(
            scenario=scenario_dict,
            sectors=results,
            biggest_movers=biggest_movers,
            metadata=metadata
        )


# ============================================================
# CONVENIENCE FUNCTIONS
# ============================================================

def create_risk_engine(data_loader: Optional[DataLoader] = None) -> RiskEngine:
    """Create a new RiskEngine instance."""
    return RiskEngine(data_loader)


def calculate_scenario(
    tariff_percent: float,
    target_partners: List[str],
    sector_filter: Optional[List[str]] = None,
    data_loader: Optional[DataLoader] = None
) -> RiskEngineResponse:
    """
    Convenience function to calculate scenario risk.
    
    Args:
        tariff_percent: Tariff increase percentage (0-25)
        target_partners: List of target partners ("US", "China", "EU")
        sector_filter: Optional list of sector IDs to include
        data_loader: Optional DataLoader instance
        
    Returns:
        Risk engine response
    """
    engine = RiskEngine(data_loader)
    
    # Convert string partners to enum
    partners = [Partner(p) for p in target_partners]
    
    scenario = ScenarioInput(
        tariff_percent=tariff_percent,
        target_partners=partners,
        sector_filter=sector_filter
    )
    
    return engine.calculate_scenario(scenario)
