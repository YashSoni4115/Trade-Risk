import { useState, useEffect, useCallback, useRef } from "react";
import { KpiStrip } from "../components/dashboard/KpiStrip";
import { RiskLeaderboard } from "../components/dashboard/RiskLeaderboard";
import { PrimaryChart } from "../components/dashboard/PrimaryChart";
import { ExplanationPanel } from "../components/dashboard/ExplanationPanel";
import {
  ScenarioControls,
  type ScenarioState,
  type ScenarioPreset,
  type SectorOption,
} from "../components/dashboard/ScenarioControls";
import { ShieldAlert } from "lucide-react";
import * as api from "../lib/api";
import type {
  RiskEngineResponse,
  SectorRiskOutput,
  SectorDetailResponse,
  SectorSummary,
  ConfigResponse,
  ScenarioInputBody,
} from "../types/api";
import type { PartnerItem } from "../types/api";

const DEFAULT_SCENARIO: ScenarioState = {
  tariffPercent: 0,
  targetPartners: ["US"],
  sectorFilter: null,
};

const PRESETS: ScenarioPreset[] = [
  {
    id: "us-steel",
    name: "US Steel Shock 2025",
    tariffPercent: 25,
    targetPartners: ["US"],
    sectorFilter: ["72", "73"],
  },
  {
    id: "eu-border",
    name: "EU Border Adjustment",
    tariffPercent: 10,
    targetPartners: ["EU"],
    sectorFilter: null,
  },
  {
    id: "china-auto",
    name: "China Autos",
    tariffPercent: 15,
    targetPartners: ["China"],
    sectorFilter: ["87"],
  },
];

// Re-export for components that import from Dashboard
export type ScenarioResultSector = SectorRiskOutput;
export type ScenarioResult = RiskEngineResponse;

export default function Dashboard() {
  const [scenario, setScenario] = useState<ScenarioState>(DEFAULT_SCENARIO);
  const [scenarioResult, setScenarioResult] = useState<RiskEngineResponse | null>(null);
  const [baselineResult, setBaselineResult] = useState<RiskEngineResponse | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sectors, setSectors] = useState<SectorOption[]>([]);
  const [partners, setPartners] = useState<PartnerItem[]>([]);
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [selectedSectorId, setSelectedSectorId] = useState<string | null>(null);
  const [sectorDetail, setSectorDetail] = useState<SectorDetailResponse | null>(null);
  const [sectorDetailLoading, setSectorDetailLoading] = useState(false);
  const skipClearResultRef = useRef(false);

  // Clear chart/result when user changes scenario inputs so we don't show stale data (e.g. "Electric" when sector is "Lumber")
  useEffect(() => {
    if (skipClearResultRef.current) {
      skipClearResultRef.current = false;
      return;
    }
    setScenarioResult(null);
    setBaselineResult(null);
  }, [scenario.sectorFilter, scenario.tariffPercent, scenario.targetPartners]);

  // Parallel load: health, config, partners, sectors on mount
  useEffect(() => {
    let cancelled = false;
    setInitialLoading(true);
    setError(null);
    Promise.all([
      api.getHealth().catch(() => null),
      api.getConfig().catch(() => null),
      api.getPartners().catch(() => ({ partners: [] })),
      api.getSectors().catch(() => ({ sectors: [] })),
    ])
      .then(([_health, cfg, partnersRes, sectorsRes]) => {
        if (cancelled) return;
        if (cfg) setConfig(cfg);
        if (partnersRes?.partners) setPartners(partnersRes.partners);
        const list = sectorsRes?.sectors ?? [];
        // Top 10 by total_exports for sector dropdown (optional; full list still used)
        const sorted = [...list].sort(
          (a, b) => (b.total_exports ?? 0) - (a.total_exports ?? 0)
        );
        setSectors(sorted.map(toSectorOption));
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load data");
      })
      .finally(() => {
        if (!cancelled) setInitialLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // Load sector detail when a row is clicked
  const onSectorClick = useCallback((sectorId: string) => {
    setSelectedSectorId(sectorId);
    setSectorDetail(null);
    setSectorDetailLoading(true);
    api
      .getSector(sectorId)
      .then((detail) => setSectorDetail(detail))
      .catch(() => setSectorDetail(null))
      .finally(() => setSectorDetailLoading(false));
  }, []);

  const onSelectPreset = useCallback((preset: ScenarioPreset) => {
    const partnerDisplayNames = preset.targetPartners.map((p) =>
      p === "US" ? "USA" : p === "China" ? "China" : p === "EU" ? "EU" : p
    );
    setScenario({
      tariffPercent: preset.tariffPercent,
      targetPartners: [...preset.targetPartners],
      sectorFilter: preset.sectorFilter === null ? null : [...preset.sectorFilter],
      partnerDisplayNames,
    });
    setError(null);
  }, []);

  const onRun = useCallback(async () => {
    setError(null);
    setIsRunning(true);
    try {
      const body: ScenarioInputBody = {
        tariff_percent: scenario.tariffPercent,
        target_partners: scenario.targetPartners,
      };
      if (scenario.sectorFilter != null && scenario.sectorFilter.length > 0) {
        body.sector_filter = scenario.sectorFilter;
      }
      const data = await api.postScenario(body);
      setScenarioResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Network error");
    } finally {
      setIsRunning(false);
    }
  }, [scenario]);

  const onLoadBaseline = useCallback(async () => {
    setError(null);
    setIsRunning(true);
    try {
      const sectorsParam =
        scenario.sectorFilter != null && scenario.sectorFilter.length > 0
          ? scenario.sectorFilter
          : undefined;
      const data = await api.getBaseline(sectorsParam);
      skipClearResultRef.current = true;
      setBaselineResult(data);
      setScenarioResult(data);
      setScenario((prev) => ({ ...prev, tariffPercent: 0 }));
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load baseline");
    } finally {
      setIsRunning(false);
    }
  }, [scenario.sectorFilter]);

  const sectorsLoading = initialLoading;

  return (
    <div className="min-h-screen bg-[#070A12] text-white font-sans selection:bg-blue-500/30">
      <header className="h-auto border-b border-white/5 flex items-center justify-between px-4 py-2 sticky top-0 bg-[#070A12]/80 backdrop-blur-md z-50">
        <div className="flex items-center gap-2">
          <div>
            <h1 className="text-xs font-semibold tracking-tight text-white/90">TradeRisk</h1>
            <p className="text-[8px] text-white/40 uppercase tracking-widest font-medium">Risk Simulation Engine</p>
          </div>
        </div>

        <ScenarioControls
          scenario={scenario}
          setScenario={setScenario}
          onRun={onRun}
          onLoadBaseline={onLoadBaseline}
          presets={PRESETS}
          onSelectPreset={onSelectPreset}
          sectors={sectors}
          partners={partners}
          sectorsLoading={sectorsLoading}
          isRunning={isRunning}
          error={error}
        />
      </header>

      <main className="p-6 max-w-[1600px] mx-auto space-y-6">
        {error && (
          <div className="rounded-lg border border-rose-500/30 bg-rose-500/10 px-4 py-2 text-sm text-rose-300" role="alert">
            {error}
          </div>
        )}

        <KpiStrip scenario={scenario} scenarioResult={scenarioResult} />

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-8 flex flex-col gap-6">
            <PrimaryChart scenarioResult={scenarioResult} baselineResult={baselineResult} />
            <RiskLeaderboard
              scenarioResult={scenarioResult}
              onSectorClick={onSectorClick}
              selectedSectorId={selectedSectorId}
            />
          </div>
          <div className="lg:col-span-4 flex flex-col gap-6">
            <ExplanationPanel
              scenario={scenario}
              scenarioResult={scenarioResult}
              sectorDetail={sectorDetail}
              sectorDetailLoading={sectorDetailLoading}
              selectedSectorId={selectedSectorId}
            />
          </div>
        </div>
      </main>
    </div>
  );
}

function toSectorOption(s: SectorSummary): SectorOption {
  return {
    sector_id: s.sector_id,
    sector_name: s.sector_name,
    total_exports: s.total_exports,
    top_partner: s.top_partner,
    top_partner_share: s.top_partner_share,
  };
}
