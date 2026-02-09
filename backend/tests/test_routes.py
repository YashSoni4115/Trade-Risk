"""
TariffShock API Routes Tests
============================
Tests for Flask API endpoints.
"""

import pytest
import json
from pathlib import Path
import sys

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.routes import create_app


@pytest.fixture
def client():
    """Create a test client for the Flask app."""
    app = create_app()
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestHealthEndpoint:
    """Test /health endpoint."""
    
    def test_health_returns_200(self, client):
        """Health check returns 200 OK."""
        response = client.get('/health')
        assert response.status_code == 200
        
    def test_health_returns_json(self, client):
        """Health check returns JSON."""
        response = client.get('/health')
        data = json.loads(response.data)
        assert 'status' in data
        assert data['status'] == 'healthy'


class TestSectorsEndpoint:
    """Test /api/sectors endpoint."""
    
    def test_sectors_returns_200(self, client):
        """Sectors endpoint returns 200 OK."""
        response = client.get('/api/sectors')
        assert response.status_code == 200
        
    def test_sectors_returns_list(self, client):
        """Sectors endpoint returns list of sectors."""
        response = client.get('/api/sectors')
        data = json.loads(response.data)
        assert 'sectors' in data
        assert isinstance(data['sectors'], list)
        assert len(data['sectors']) > 0
        
    def test_sectors_have_required_fields(self, client):
        """Each sector has required fields."""
        response = client.get('/api/sectors')
        data = json.loads(response.data)
        sector = data['sectors'][0]
        assert 'sector_id' in sector
        assert 'sector_name' in sector


class TestSectorDetailEndpoint:
    """Test /api/sector/<id> endpoint."""
    
    def test_sector_detail_valid_id(self, client):
        """Sector detail returns data for valid ID."""
        response = client.get('/api/sector/87')  # Vehicles
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['sector_id'] == '87'
        
    def test_sector_detail_has_partner_shares(self, client):
        """Sector detail includes partner_shares."""
        response = client.get('/api/sector/87')
        data = json.loads(response.data)
        assert 'partner_shares' in data
        assert 'US' in data['partner_shares']
        
    def test_sector_detail_invalid_id(self, client):
        """Sector detail returns 404 for invalid ID."""
        response = client.get('/api/sector/99999')
        assert response.status_code == 404


class TestBaselineEndpoint:
    """Test /api/baseline endpoint."""
    
    def test_baseline_returns_200(self, client):
        """Baseline endpoint returns 200 OK."""
        response = client.get('/api/baseline')
        assert response.status_code == 200
        
    def test_baseline_all_zero_risk(self, client):
        """Baseline has zero risk for all sectors."""
        response = client.get('/api/baseline')
        data = json.loads(response.data)
        assert 'sectors' in data
        for sector in data['sectors']:
            assert sector['risk_score'] == 0.0


class TestScenarioEndpoint:
    """Test /api/scenario endpoint."""
    
    def test_scenario_valid_input(self, client):
        """Scenario accepts valid input."""
        payload = {
            "tariff_percent": 10,
            "target_partners": ["US"]
        }
        response = client.post(
            '/api/scenario',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == 200
        
    def test_scenario_returns_sectors(self, client):
        """Scenario returns sector risk data."""
        payload = {
            "tariff_percent": 10,
            "target_partners": ["US"]
        }
        response = client.post(
            '/api/scenario',
            data=json.dumps(payload),
            content_type='application/json'
        )
        data = json.loads(response.data)
        assert 'sectors' in data
        assert len(data['sectors']) > 0
        
    def test_scenario_sectors_sorted_by_risk(self, client):
        """Scenario returns sectors sorted by risk descending."""
        payload = {
            "tariff_percent": 25,
            "target_partners": ["US"]
        }
        response = client.post(
            '/api/scenario',
            data=json.dumps(payload),
            content_type='application/json'
        )
        data = json.loads(response.data)
        risks = [s['risk_score'] for s in data['sectors']]
        assert risks == sorted(risks, reverse=True)
        
    def test_scenario_missing_tariff_percent(self, client):
        """Scenario rejects missing tariff_percent."""
        payload = {"target_partners": ["US"]}
        response = client.post(
            '/api/scenario',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == 400
        
    def test_scenario_negative_tariff(self, client):
        """Scenario rejects negative tariff."""
        payload = {
            "tariff_percent": -5,
            "target_partners": ["US"]
        }
        response = client.post(
            '/api/scenario',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == 400
        
    def test_scenario_tariff_too_high(self, client):
        """Scenario rejects tariff > 100."""
        payload = {
            "tariff_percent": 150,
            "target_partners": ["US"]
        }
        response = client.post(
            '/api/scenario',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == 400
        
    def test_scenario_multiple_partners(self, client):
        """Scenario accepts multiple target partners."""
        payload = {
            "tariff_percent": 20,
            "target_partners": ["US", "China"]
        }
        response = client.post(
            '/api/scenario',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == 200


class TestCompareEndpoint:
    """Test /api/compare endpoint."""
    
    def test_compare_valid_input(self, client):
        """Compare accepts valid input."""
        payload = {
            "baseline": {"tariff_percent": 0, "target_partners": []},
            "scenario": {"tariff_percent": 10, "target_partners": ["US"]}
        }
        response = client.post(
            '/api/compare',
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == 200
        
    def test_compare_has_baseline_and_shocked(self, client):
        """Compare returns both baseline and shocked."""
        payload = {
            "baseline": {"tariff_percent": 0, "target_partners": []},
            "scenario": {"tariff_percent": 10, "target_partners": ["US"]}
        }
        response = client.post(
            '/api/compare',
            data=json.dumps(payload),
            content_type='application/json'
        )
        data = json.loads(response.data)
        assert 'comparison' in data
        assert 'baseline_scenario' in data
        assert 'shock_scenario' in data
        
    def test_compare_shocked_risk_higher(self, client):
        """Compare shows shocked risk > baseline for high US exposure sectors."""
        payload = {
            "baseline": {"tariff_percent": 0, "target_partners": []},
            "scenario": {"tariff_percent": 25, "target_partners": ["US"]}
        }
        response = client.post(
            '/api/compare',
            data=json.dumps(payload),
            content_type='application/json'
        )
        data = json.loads(response.data)
        
        # Check that comparison has sectors with risk changes
        comparison = data['comparison']
        assert len(comparison) > 0
        # At least some sectors should have positive risk change
        assert any(s['risk_change'] > 0 for s in comparison)


class TestActualTariffsEndpoint:
    """Test /api/actual-tariffs endpoint."""
    
    def test_actual_tariffs_returns_200(self, client):
        """Actual tariffs endpoint returns 200 OK."""
        response = client.get('/api/actual-tariffs')
        assert response.status_code == 200
        
    def test_actual_tariffs_has_sectors(self, client):
        """Actual tariffs returns sector data."""
        response = client.get('/api/actual-tariffs')
        data = json.loads(response.data)
        assert 'sectors' in data
        assert len(data['sectors']) > 0
        
    def test_actual_tariffs_steel_has_risk(self, client):
        """Steel sector (72/73) has risk due to 25% US tariff."""
        response = client.get('/api/actual-tariffs')
        data = json.loads(response.data)
        sectors = {s['sector_id']: s for s in data['sectors']}
        
        # Check steel (72) or iron/steel (73)
        steel_sectors = [s for sid, s in sectors.items() if sid in ['72', '73']]
        if steel_sectors:
            # At least one steel sector should have non-zero risk
            assert any(s['risk_score'] > 0 for s in steel_sectors)


class TestTariffRatesEndpoint:
    """Test /api/tariff-rates endpoint."""
    
    def test_tariff_rates_returns_200(self, client):
        """Tariff rates endpoint returns 200 OK."""
        response = client.get('/api/tariff-rates')
        assert response.status_code == 200
        
    def test_tariff_rates_has_partners(self, client):
        """Tariff rates includes all partners."""
        response = client.get('/api/tariff-rates')
        data = json.loads(response.data)
        assert 'tariffs' in data
        # Check that tariffs have data for major partners
        tariff = data['tariffs'][0]
        assert 'tariff_rates' in tariff
        
    def test_tariff_rates_us_has_steel(self, client):
        """US tariffs include steel at 25%."""
        response = client.get('/api/tariff-rates')
        data = json.loads(response.data)
        
        # Check for steel sectors (72 or 73)
        steel_tariffs = [t for t in data['tariffs'] if t['hs2'] in ['72', '73']]
        if steel_tariffs:
            assert any(t['tariff_rates']['US'] == 25.0 for t in steel_tariffs)


class TestPartnersEndpoint:
    """Test /api/partners endpoint."""
    
    def test_partners_returns_200(self, client):
        """Partners endpoint returns 200 OK."""
        response = client.get('/api/partners')
        assert response.status_code == 200
        
    def test_partners_includes_major_partners(self, client):
        """Partners includes US, China, EU."""
        response = client.get('/api/partners')
        data = json.loads(response.data)
        assert 'partners' in data
        partners = data['partners']
        partner_ids = [p['id'] for p in partners]
        assert 'US' in partner_ids
        assert 'China' in partner_ids
        assert 'EU' in partner_ids


class TestConfigEndpoint:
    """Test /api/config endpoint."""
    
    def test_config_returns_200(self, client):
        """Config endpoint returns 200 OK."""
        response = client.get('/api/config')
        assert response.status_code == 200
        
    def test_config_has_weights(self, client):
        """Config includes risk calculation weights."""
        response = client.get('/api/config')
        data = json.loads(response.data)
        assert 'w_exposure' in data
        assert 'w_concentration' in data
        
    def test_config_weights_sum_to_one(self, client):
        """Config weights sum to 1.0."""
        response = client.get('/api/config')
        data = json.loads(response.data)
        weight_sum = data['w_exposure'] + data['w_concentration']
        assert abs(weight_sum - 1.0) < 0.001


class TestErrorHandling:
    """Test error handling."""
    
    def test_404_for_unknown_route(self, client):
        """Unknown routes return 404."""
        response = client.get('/api/unknown')
        assert response.status_code == 404
        
    def test_405_for_wrong_method(self, client):
        """Wrong HTTP method returns 405."""
        response = client.post('/api/sectors')
        assert response.status_code == 405
        
    def test_invalid_json_returns_400(self, client):
        """Invalid JSON returns 400."""
        response = client.post(
            '/api/scenario',
            data='not valid json',
            content_type='application/json'
        )
        assert response.status_code == 400
