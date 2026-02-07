"""
TariffShock Risk Engine Unit Tests
==================================
Tests for the deterministic risk calculation engine.

Required tests per spec:
- Exposure correctness
- Risk monotonicity (higher tariffs never lower risk)
- Risk bounds (0 to 100)
- Golden test (known sector and scenario must produce fixed expected output)
"""

import pytest
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas import (
    Partner,
    SectorSummary,
    ScenarioInput,
    SectorPartnerExport,
    ExplainabilityOutput,
    SectorRiskOutput
)
from src.risk_engine import (
    RiskEngine,
    W_EXPOSURE,
    W_CONCENTRATION,
    MAX_TARIFF_PERCENT,
    calculate_scenario
)


# ============================================================
# TEST FIXTURES
# ============================================================

@pytest.fixture
def sample_sector() -> SectorSummary:
    """Create a sample sector for testing."""
    return SectorSummary(
        sector_id="87",
        sector_name="Vehicles",
        total_exports=50_000_000_000,  # $50B
        partner_shares={
            "US": 0.62,
            "China": 0.08,
            "EU": 0.15,
            "Other": 0.15
        },
        top_partner=Partner.US,
        top_partner_share=0.62
    )


@pytest.fixture
def sample_sector_low_us() -> SectorSummary:
    """Create a sector with low US exposure."""
    return SectorSummary(
        sector_id="30",
        sector_name="Pharmaceuticals",
        total_exports=10_000_000_000,  # $10B
        partner_shares={
            "US": 0.20,
            "China": 0.30,
            "EU": 0.40,
            "Other": 0.10
        },
        top_partner=Partner.EU,
        top_partner_share=0.40
    )


@pytest.fixture
def mock_engine(sample_sector, sample_sector_low_us):
    """Create a mock risk engine with test data."""
    from src.load_data import DataLoader
    
    class MockDataLoader(DataLoader):
        def __init__(self):
            super().__init__()
            self._is_loaded = True
            self._sector_summaries = {
                "87": sample_sector,
                "30": sample_sector_low_us
            }
            self._sector_partner_exports = []
    
    return RiskEngine(MockDataLoader())


# ============================================================
# SCHEMA VALIDATION TESTS
# ============================================================

class TestSchemaValidation:
    """Test input validation schemas."""
    
    def test_sector_partner_export_valid(self):
        """Valid sector partner export should pass."""
        export = SectorPartnerExport(
            sector_id="87",
            sector_name="Vehicles",
            partner=Partner.US,
            export_value=1000000
        )
        assert export.export_value == 1000000
    
    def test_sector_partner_export_negative_value_fails(self):
        """Negative export value should fail."""
        with pytest.raises(ValueError, match="export_value must be >= 0"):
            SectorPartnerExport(
                sector_id="87",
                sector_name="Vehicles",
                partner=Partner.US,
                export_value=-1000
            )
    
    def test_sector_summary_invalid_top_partner_share(self):
        """Top partner share > 1 should fail."""
        with pytest.raises(ValueError, match="top_partner_share must be in"):
            SectorSummary(
                sector_id="01",
                sector_name="Test",
                total_exports=1000,
                partner_shares={"US": 1.0, "China": 0, "EU": 0, "Other": 0},
                top_partner=Partner.US,
                top_partner_share=1.5
            )
    
    def test_scenario_input_valid(self):
        """Valid scenario input should pass."""
        scenario = ScenarioInput(
            tariff_percent=10,
            target_partners=[Partner.US, Partner.CHINA]
        )
        assert scenario.tariff_percent == 10
        assert len(scenario.target_partners) == 2
    
    def test_scenario_input_tariff_too_high(self):
        """Tariff > 25 should fail."""
        with pytest.raises(ValueError, match="tariff_percent must be in"):
            ScenarioInput(
                tariff_percent=30,
                target_partners=[Partner.US]
            )
    
    def test_scenario_input_tariff_negative(self):
        """Negative tariff should fail."""
        with pytest.raises(ValueError, match="tariff_percent must be in"):
            ScenarioInput(
                tariff_percent=-5,
                target_partners=[Partner.US]
            )


# ============================================================
# EXPOSURE CALCULATION TESTS
# ============================================================

class TestExposureCalculation:
    """Test exposure calculation correctness."""
    
    def test_exposure_single_partner(self, mock_engine, sample_sector):
        """Exposure to single partner should equal partner share."""
        exposure = mock_engine.calculate_exposure(
            sample_sector, 
            [Partner.US]
        )
        assert exposure == 0.62
    
    def test_exposure_multiple_partners(self, mock_engine, sample_sector):
        """Exposure to multiple partners should sum shares."""
        exposure = mock_engine.calculate_exposure(
            sample_sector, 
            [Partner.US, Partner.CHINA]
        )
        assert exposure == 0.62 + 0.08  # 0.70
    
    def test_exposure_all_partners(self, mock_engine, sample_sector):
        """Exposure to all partners should sum to ~1."""
        exposure = mock_engine.calculate_exposure(
            sample_sector, 
            [Partner.US, Partner.CHINA, Partner.EU]
        )
        assert exposure == pytest.approx(0.62 + 0.08 + 0.15, rel=0.01)
    
    def test_exposure_empty_partners(self, mock_engine, sample_sector):
        """Exposure with no partners should be 0."""
        exposure = mock_engine.calculate_exposure(sample_sector, [])
        assert exposure == 0.0
    
    def test_exposure_clamped_to_one(self, mock_engine, sample_sector):
        """Exposure should be clamped to max 1.0 even with all partners."""
        # Test that selecting all partners gives exposure capped at 1.0
        exposure = mock_engine.calculate_exposure(
            sample_sector, 
            [Partner.US, Partner.CHINA, Partner.EU, Partner.OTHER]
        )
        # Even with Other included, should be <= 1.0
        assert exposure <= 1.0


# ============================================================
# CONCENTRATION CALCULATION TESTS
# ============================================================

class TestConcentrationCalculation:
    """Test concentration calculation."""
    
    def test_concentration_equals_top_partner_share(self, mock_engine, sample_sector):
        """Concentration should equal top partner share."""
        concentration = mock_engine.calculate_concentration(sample_sector)
        assert concentration == 0.62
    
    def test_concentration_different_sector(self, mock_engine, sample_sector_low_us):
        """Concentration should vary by sector."""
        concentration = mock_engine.calculate_concentration(sample_sector_low_us)
        assert concentration == 0.40


# ============================================================
# SHOCK CALCULATION TESTS
# ============================================================

class TestShockCalculation:
    """Test shock normalization."""
    
    def test_shock_zero_tariff(self, mock_engine):
        """Zero tariff should produce zero shock."""
        shock = mock_engine.calculate_shock(0)
        assert shock == 0.0
    
    def test_shock_max_tariff(self, mock_engine):
        """Max tariff (25%) should produce shock of 1."""
        shock = mock_engine.calculate_shock(25)
        assert shock == 1.0
    
    def test_shock_mid_tariff(self, mock_engine):
        """10% tariff should produce shock of 0.4."""
        shock = mock_engine.calculate_shock(10)
        assert shock == pytest.approx(0.4, rel=0.01)


# ============================================================
# RISK SCORE CALCULATION TESTS
# ============================================================

class TestRiskScoreCalculation:
    """Test risk score calculation."""
    
    def test_risk_score_zero_shock(self, mock_engine):
        """Zero shock should produce zero risk."""
        risk = mock_engine.calculate_risk_score(
            exposure=0.62, 
            concentration=0.62, 
            shock=0
        )
        assert risk == 0.0
    
    def test_risk_score_max_everything(self, mock_engine):
        """Max values should produce risk of 100."""
        risk = mock_engine.calculate_risk_score(
            exposure=1.0, 
            concentration=1.0, 
            shock=1.0
        )
        assert risk == 100.0
    
    def test_risk_score_formula_correctness(self, mock_engine):
        """Risk score should follow the formula exactly."""
        exposure = 0.62
        concentration = 0.62
        shock = 0.4  # 10% tariff
        
        expected_raw = (W_EXPOSURE * exposure + W_CONCENTRATION * concentration) * shock
        expected_score = round(expected_raw * 100, 1)
        
        actual = mock_engine.calculate_risk_score(exposure, concentration, shock)
        assert actual == expected_score


# ============================================================
# RISK MONOTONICITY TESTS
# ============================================================

class TestRiskMonotonicity:
    """Test that higher tariffs never lower risk."""
    
    def test_risk_increases_with_tariff(self, mock_engine, sample_sector):
        """Risk should increase or stay same as tariff increases."""
        target_partners = [Partner.US]
        
        prev_risk = 0
        for tariff in range(0, 26, 5):  # 0, 5, 10, 15, 20, 25
            scenario = ScenarioInput(
                tariff_percent=tariff,
                target_partners=target_partners
            )
            result = mock_engine.calculate_sector_risk(sample_sector, scenario)
            
            assert result.risk_score >= prev_risk, \
                f"Risk decreased from {prev_risk} to {result.risk_score} at tariff {tariff}%"
            prev_risk = result.risk_score
    
    def test_risk_monotonic_with_more_partners(self, mock_engine, sample_sector):
        """Risk should increase or stay same with more target partners."""
        tariff = 10
        
        # Single partner
        scenario1 = ScenarioInput(tariff_percent=tariff, target_partners=[Partner.US])
        result1 = mock_engine.calculate_sector_risk(sample_sector, scenario1)
        
        # Two partners
        scenario2 = ScenarioInput(tariff_percent=tariff, target_partners=[Partner.US, Partner.CHINA])
        result2 = mock_engine.calculate_sector_risk(sample_sector, scenario2)
        
        # More partners = more exposure = higher risk
        assert result2.risk_score >= result1.risk_score


# ============================================================
# RISK BOUNDS TESTS
# ============================================================

class TestRiskBounds:
    """Test that risk scores are within valid bounds."""
    
    def test_risk_minimum_bound(self, mock_engine, sample_sector):
        """Risk score should never be negative."""
        scenario = ScenarioInput(tariff_percent=0, target_partners=[])
        result = mock_engine.calculate_sector_risk(sample_sector, scenario)
        assert result.risk_score >= 0
    
    def test_risk_maximum_bound(self, mock_engine, sample_sector):
        """Risk score should never exceed 100."""
        scenario = ScenarioInput(
            tariff_percent=25, 
            target_partners=[Partner.US, Partner.CHINA, Partner.EU]
        )
        result = mock_engine.calculate_sector_risk(sample_sector, scenario)
        assert result.risk_score <= 100
    
    def test_all_output_values_bounded(self, mock_engine, sample_sector):
        """All output values should be within expected ranges."""
        scenario = ScenarioInput(tariff_percent=15, target_partners=[Partner.US])
        result = mock_engine.calculate_sector_risk(sample_sector, scenario)
        
        assert 0 <= result.risk_score <= 100
        assert 0 <= result.exposure <= 1
        assert 0 <= result.concentration <= 1
        assert 0 <= result.shock <= 1
        assert 0 <= result.dependency_percent <= 100
        assert result.affected_export_value >= 0


# ============================================================
# GOLDEN TEST
# ============================================================

class TestGoldenOutput:
    """
    Golden test with known inputs producing fixed expected outputs.
    
    This test ensures the calculation logic doesn't change unexpectedly.
    """
    
    def test_golden_scenario(self, mock_engine):
        """
        Golden test case:
        - Sector: Vehicles (87)
        - Partner shares: US=0.62, China=0.08, EU=0.15, Other=0.15
        - Top partner: US (0.62)
        - Total exports: $50B
        - Scenario: 10% tariff on US
        """
        sector = SectorSummary(
            sector_id="87",
            sector_name="Vehicles",
            total_exports=50_000_000_000,
            partner_shares={"US": 0.62, "China": 0.08, "EU": 0.15, "Other": 0.15},
            top_partner=Partner.US,
            top_partner_share=0.62
        )
        
        scenario = ScenarioInput(
            tariff_percent=10,
            target_partners=[Partner.US]
        )
        
        result = mock_engine.calculate_sector_risk(sector, scenario)
        
        # Expected calculations:
        # exposure = 0.62 (US only)
        # concentration = 0.62 (top partner share)
        # shock = 10/25 = 0.4
        # risk_raw = (0.6 * 0.62 + 0.4 * 0.62) * 0.4 = (0.372 + 0.248) * 0.4 = 0.248
        # risk_score = 0.248 * 100 = 24.8
        
        expected_exposure = 0.62
        expected_concentration = 0.62
        expected_shock = 0.4
        expected_risk_raw = (W_EXPOSURE * expected_exposure + W_CONCENTRATION * expected_concentration) * expected_shock
        expected_risk_score = round(expected_risk_raw * 100, 1)
        
        assert result.sector_id == "87"
        assert result.sector_name == "Vehicles"
        assert result.exposure == expected_exposure
        assert result.concentration == expected_concentration
        assert result.shock == expected_shock
        assert result.risk_score == expected_risk_score
        assert result.top_partner == "US"
        assert result.dependency_percent == 62.0
        
        # Affected export value = $50B * 0.62 * 0.4 = $12.4B
        expected_affected = 50_000_000_000 * 0.62 * 0.4
        assert result.affected_export_value == expected_affected
        
        # Explainability checks
        assert result.explainability.exposure_value == expected_exposure
        assert result.explainability.concentration_value == expected_concentration
        assert result.explainability.shock_value == expected_shock
        assert result.explainability.exposure_component == pytest.approx(W_EXPOSURE * expected_exposure, rel=0.01)
        assert result.explainability.concentration_component == pytest.approx(W_CONCENTRATION * expected_concentration, rel=0.01)


# ============================================================
# AFFECTED EXPORT VALUE TESTS
# ============================================================

class TestAffectedExportValue:
    """Test affected export value calculation."""
    
    def test_affected_value_zero_shock(self, mock_engine, sample_sector):
        """Zero shock should produce zero affected value."""
        affected = mock_engine.calculate_affected_export_value(
            total_exports=50_000_000_000,
            exposure=0.62,
            shock=0
        )
        assert affected == 0.0
    
    def test_affected_value_zero_exposure(self, mock_engine, sample_sector):
        """Zero exposure should produce zero affected value."""
        affected = mock_engine.calculate_affected_export_value(
            total_exports=50_000_000_000,
            exposure=0,
            shock=0.4
        )
        assert affected == 0.0
    
    def test_affected_value_formula(self, mock_engine):
        """Affected value should follow the formula."""
        total = 100_000_000
        exposure = 0.5
        shock = 0.4
        
        expected = total * exposure * shock
        actual = mock_engine.calculate_affected_export_value(total, exposure, shock)
        
        assert actual == expected


# ============================================================
# SCENARIO RESPONSE TESTS
# ============================================================

class TestScenarioResponse:
    """Test complete scenario response."""
    
    def test_scenario_response_structure(self, mock_engine):
        """Response should have all required fields."""
        scenario = ScenarioInput(
            tariff_percent=10,
            target_partners=[Partner.US]
        )
        response = mock_engine.calculate_scenario(scenario)
        
        assert 'tariff_percent' in response.scenario
        assert 'target_partners' in response.scenario
        assert len(response.sectors) > 0
        assert len(response.biggest_movers) <= 5
        assert 'w_exposure' in response.metadata
        assert 'w_concentration' in response.metadata
    
    def test_sectors_sorted_by_risk(self, mock_engine):
        """Sectors should be sorted by risk score descending."""
        scenario = ScenarioInput(
            tariff_percent=10,
            target_partners=[Partner.US]
        )
        response = mock_engine.calculate_scenario(scenario)
        
        risk_scores = [s.risk_score for s in response.sectors]
        assert risk_scores == sorted(risk_scores, reverse=True)
    
    def test_sector_filter_works(self, mock_engine):
        """Sector filter should limit results."""
        scenario = ScenarioInput(
            tariff_percent=10,
            target_partners=[Partner.US],
            sector_filter=["87"]
        )
        response = mock_engine.calculate_scenario(scenario)
        
        assert len(response.sectors) == 1
        assert response.sectors[0].sector_id == "87"


# ============================================================
# BASELINE TESTS
# ============================================================

class TestBaseline:
    """Test baseline calculation."""
    
    def test_baseline_zero_risk(self, mock_engine):
        """Baseline (tariff=0) should produce zero risk."""
        response = mock_engine.get_baseline()
        
        for sector in response.sectors:
            assert sector.risk_score == 0.0
            assert sector.risk_delta == 0.0


# ============================================================
# EDGE CASES
# ============================================================

class TestEdgeCases:
    """Test edge cases and error handling."""
    
    def test_unknown_sector_ignored(self, mock_engine):
        """Unknown sector IDs should be ignored."""
        scenario = ScenarioInput(
            tariff_percent=10,
            target_partners=[Partner.US],
            sector_filter=["UNKNOWN", "87"]
        )
        response = mock_engine.calculate_scenario(scenario)
        
        # Should only return sector 87
        assert len(response.sectors) == 1
        assert response.sectors[0].sector_id == "87"
    
    def test_empty_filter_returns_all(self, mock_engine):
        """Empty sector filter should return all sectors."""
        scenario = ScenarioInput(
            tariff_percent=10,
            target_partners=[Partner.US],
            sector_filter=None
        )
        response = mock_engine.calculate_scenario(scenario)
        
        assert len(response.sectors) == 2  # Mock has 2 sectors


# ============================================================
# CONFIGURATION TESTS
# ============================================================

class TestConfiguration:
    """Test configuration parameters."""
    
    def test_weights_sum_to_one(self):
        """Weights must sum to 1."""
        assert W_EXPOSURE + W_CONCENTRATION == 1.0
    
    def test_weight_values(self):
        """Check expected weight values."""
        assert W_EXPOSURE == 0.6
        assert W_CONCENTRATION == 0.4
    
    def test_max_tariff(self):
        """Check max tariff value."""
        assert MAX_TARIFF_PERCENT == 25.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
