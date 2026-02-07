"""
TariffShock Input Validation Schemas
====================================
Defines data validation schemas for the Risk Engine.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal
from enum import Enum


class Partner(str, Enum):
    """Valid trading partner enum."""
    US = "US"
    CHINA = "China"
    EU = "EU"
    OTHER = "Other"


@dataclass
class SectorPartnerExport:
    """
    Sector Partner Export record.
    
    Constraints:
    - export_value must be >= 0
    - each (sector_id, partner) combination must be unique
    """
    sector_id: str
    sector_name: str
    partner: Partner
    export_value: float
    
    def __post_init__(self):
        if self.export_value < 0:
            raise ValueError(f"export_value must be >= 0, got {self.export_value}")
        if not self.sector_id:
            raise ValueError("sector_id cannot be empty")
        if not self.sector_name:
            raise ValueError("sector_name cannot be empty")


@dataclass
class SectorSummary:
    """
    Sector Summary record (derived or precomputed).
    
    Constraints:
    - partner shares must sum to approximately 1
    - top_partner_share must be within [0, 1]
    """
    sector_id: str
    sector_name: str
    total_exports: float
    partner_shares: Dict[str, float]  # {US: 0.62, China: 0.08, EU: 0.15, Other: 0.15}
    top_partner: Partner
    top_partner_share: float
    
    def __post_init__(self):
        if self.total_exports < 0:
            raise ValueError(f"total_exports must be >= 0, got {self.total_exports}")
        
        if not 0 <= self.top_partner_share <= 1:
            raise ValueError(f"top_partner_share must be in [0, 1], got {self.top_partner_share}")
        
        # Validate partner shares sum to approximately 1
        shares_sum = sum(self.partner_shares.values())
        if not 0.99 <= shares_sum <= 1.01:
            raise ValueError(f"partner_shares must sum to ~1, got {shares_sum}")


@dataclass
class ScenarioInput:
    """
    Scenario input for risk calculation.
    
    Constraints:
    - tariff_percent must be in range [0, 25]
    - empty target_partners means zero exposure
    """
    tariff_percent: float
    target_partners: List[Partner]
    sector_filter: Optional[List[str]] = None
    
    def __post_init__(self):
        if not 0 <= self.tariff_percent <= 25:
            raise ValueError(f"tariff_percent must be in [0, 25], got {self.tariff_percent}")
        
        # Convert string partners to enum if needed
        self.target_partners = [
            Partner(p) if isinstance(p, str) else p 
            for p in self.target_partners
        ]


@dataclass
class ExplainabilityOutput:
    """Explainability output for a sector's risk calculation."""
    exposure_value: float
    concentration_value: float
    shock_value: float
    exposure_component: float  # w_exposure * exposure
    concentration_component: float  # w_concentration * concentration


@dataclass
class SectorRiskOutput:
    """
    Output schema for a single sector's risk calculation.
    
    Required output fields per spec.
    """
    sector_id: str
    sector_name: str
    risk_score: float  # 0-100, rounded to 1 decimal
    risk_delta: float
    exposure: float
    concentration: float
    shock: float
    top_partner: str
    dependency_percent: float  # top_partner_share * 100
    affected_export_value: float  # proxy, labeled as such
    explainability: ExplainabilityOutput
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "sector_id": self.sector_id,
            "sector_name": self.sector_name,
            "risk_score": self.risk_score,
            "risk_delta": self.risk_delta,
            "exposure": self.exposure,
            "concentration": self.concentration,
            "shock": self.shock,
            "top_partner": self.top_partner,
            "dependency_percent": self.dependency_percent,
            "affected_export_value": self.affected_export_value,
            "affected_export_value_note": "This is a proxy estimate",
            "explainability": {
                "exposure_value": self.explainability.exposure_value,
                "concentration_value": self.explainability.concentration_value,
                "shock_value": self.explainability.shock_value,
                "exposure_component": self.explainability.exposure_component,
                "concentration_component": self.explainability.concentration_component
            }
        }


@dataclass
class RiskEngineResponse:
    """Complete response from the risk engine."""
    scenario: Dict
    sectors: List[SectorRiskOutput]
    biggest_movers: List[SectorRiskOutput]
    metadata: Dict = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "scenario": self.scenario,
            "sectors": [s.to_dict() for s in self.sectors],
            "biggest_movers": [s.to_dict() for s in self.biggest_movers],
            "metadata": self.metadata
        }
