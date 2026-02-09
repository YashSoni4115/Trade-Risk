/**
 * Backend DTO types (mirror Flask API responses).
 * Optional fields used where backend may omit them.
 */

export interface HealthResponse {
  status?: string;
  engine_loaded?: boolean;
}

export interface PartnerItem {
  id: string;
  name: string;
}

export interface PartnersResponse {
  partners: PartnerItem[];
  note?: string;
}

export interface ConfigResponse {
  w_exposure?: number;
  w_concentration?: number;
  max_tariff_percent?: number;
  risk_formula?: string;
  shock_formula?: string;
  ml_model_available?: boolean;
  ml_model_note?: string;
}

export interface SectorSummary {
  sector_id: string;
  sector_name: string;
  total_exports?: number;
  top_partner?: string;
  top_partner_share?: number;
}

export interface SectorsResponse {
  count?: number;
  sectors: SectorSummary[];
}

export interface SectorDetailResponse {
  sector_id: string;
  sector_name: string;
  total_exports: number;
  partner_shares: Record<string, number>;
  top_partner: string;
  top_partner_share: number;
}

export interface ScenarioInputBody {
  tariff_percent: number;
  target_partners: string[];
  sector_filter?: string[] | null;
}

export interface ExplainabilityOutput {
  exposure_value: number;
  concentration_value: number;
  shock_value: number;
  exposure_component: number;
  concentration_component: number;
}

export interface SectorRiskOutput {
  sector_id: string;
  sector_name: string;
  risk_score: number;
  risk_delta: number;
  exposure: number;
  concentration: number;
  shock: number;
  top_partner: string;
  dependency_percent: number;
  affected_export_value: number;
  affected_export_value_note?: string;
  explainability?: ExplainabilityOutput;
}

export interface RiskEngineResponse {
  scenario: Record<string, unknown>;
  sectors: SectorRiskOutput[];
  biggest_movers: SectorRiskOutput[];
  metadata?: Record<string, unknown>;
}

export interface CompareSectorRow {
  sector_id: string;
  sector_name: string;
  baseline_risk: number;
  scenario_risk: number;
  risk_change: number;
  affected_export_value: number;
  top_partner: string;
  dependency_percent: number;
}

export interface CompareResponse {
  baseline_scenario: Record<string, unknown>;
  shock_scenario: Record<string, unknown>;
  comparison: CompareSectorRow[];
  biggest_gainers: CompareSectorRow[];
  total_sectors: number;
}
