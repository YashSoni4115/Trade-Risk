/**
 * API client for TariffShock Flask backend.
 * Base URL from VITE_API_BASE_URL (default http://localhost:5001).
 */

import type {
  HealthResponse,
  ConfigResponse,
  PartnersResponse,
  SectorsResponse,
  SectorDetailResponse,
  ScenarioInputBody,
  RiskEngineResponse,
  CompareResponse,
} from "../types/api";

const getBaseUrl = (): string => {
  // In production (Vercel), use empty string for relative paths
  // In development, default to localhost:5001
  if (typeof import.meta.env !== "undefined" && import.meta.env?.VITE_API_BASE_URL !== undefined) {
    const url = String(import.meta.env.VITE_API_BASE_URL).replace(/\/$/, "");
    return url || ""; // Empty string means relative paths
  }
  return "http://localhost:5001";
};

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const base = getBaseUrl();
  const url = path.startsWith("http") ? path : `${base}${path}`;
  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers,
    },
  });
  let body: unknown;
  const ct = res.headers.get("content-type");
  if (ct?.includes("application/json")) {
    try {
      body = await res.json();
    } catch {
      body = null;
    }
  } else {
    body = await res.text();
  }
  if (!res.ok) {
    const msg =
      typeof body === "object" && body !== null && "error" in body
        ? String((body as { error?: string }).error)
        : typeof body === "string" && body
          ? body
          : `Request failed: ${res.status}`;
    throw new Error(msg);
  }
  return body as T;
}

export function apiBaseUrl(): string {
  return getBaseUrl();
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getConfig(): Promise<ConfigResponse> {
  return request<ConfigResponse>("/api/config");
}

export function getPartners(): Promise<PartnersResponse> {
  return request<PartnersResponse>("/api/partners");
}

export function getSectors(): Promise<SectorsResponse> {
  return request<SectorsResponse>("/api/sectors");
}

export function getSector(sectorId: string): Promise<SectorDetailResponse> {
  return request<SectorDetailResponse>(`/api/sector/${encodeURIComponent(sectorId)}`);
}

export function getBaseline(sectors?: string[]): Promise<RiskEngineResponse> {
  const qs = sectors?.length ? `?sectors=${sectors.map((s) => encodeURIComponent(s)).join(",")}` : "";
  return request<RiskEngineResponse>(`/api/baseline${qs}`);
}

export function postScenario(body: ScenarioInputBody): Promise<RiskEngineResponse> {
  return request<RiskEngineResponse>("/api/scenario", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function postCompare(body: {
  baseline: Record<string, unknown>;
  scenario: Record<string, unknown>;
  sector_filter?: string[] | null;
}): Promise<CompareResponse> {
  return request<CompareResponse>("/api/compare", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getActualTariffs(params?: {
  partners?: string;
  sectors?: string;
}): Promise<RiskEngineResponse> {
  const sp = new URLSearchParams();
  if (params?.partners) sp.set("partners", params.partners);
  if (params?.sectors) sp.set("sectors", params.sectors);
  const qs = sp.toString() ? `?${sp.toString()}` : "";
  return request<RiskEngineResponse>(`/api/actual-tariffs${qs}`);
}

export function getTariffRates(): Promise<{
  description?: string;
  sectors?: Array<{ hs2: string; sector_name: string; tariff_rates: Record<string, number>; max_tariff: number }>;
}> {
  return request("/api/tariff-rates");
}
