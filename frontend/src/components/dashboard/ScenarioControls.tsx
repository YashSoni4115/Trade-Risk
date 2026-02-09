import { useState, useCallback, useMemo } from "react";
import { Play, RotateCcw, ChevronDown, Search, X, Plus } from "lucide-react";

export interface SectorTariff {
  sector_id: string;
  tariff_percent: number;
}

export interface ScenarioState {
  tariffPercent: number;
  targetPartners: string[];
  sectorFilter: string[] | null;
  /** Display names for UI; used to show "EU (via Germany)" and detect unsupported partners */
  partnerDisplayNames?: string[];
  /** Multi-sector tariffs: array of {sector_id, tariff_percent} pairs */
  sectorTariffs?: SectorTariff[];
}

export interface ScenarioPreset {
  id: string;
  name: string;
  tariffPercent: number;
  targetPartners: string[];
  sectorFilter: string[] | null;
}

export interface SectorOption {
  sector_id: string;
  sector_name: string;
  total_exports?: number;
  top_partner?: string;
  top_partner_share?: number;
}

export interface PartnerItem {
  id: string;
  name: string;
}

// --- Partner mapping (backend supports only US, China, EU) ---
const TOP_PARTNERS_DISPLAY: string[] = [
  "USA",
  "China",
  "United Kingdom",
  "Japan",
  "Mexico",
  "Germany",
  "South Korea",
  "Netherlands",
  "India",
  "France",
];

const EU_COUNTRIES = new Set([
  "Germany",
  "France",
  "Netherlands",
  "Italy",
  "Spain",
  "Belgium",
  "Poland",
  "Austria",
  "Ireland",
  "Portugal",
  "Greece",
  "Romania",
  "Czech Republic",
  "Hungary",
  "Sweden",
  "Denmark",
  "Finland",
]);

const UNSUPPORTED_NON_EU = new Set([
  "United Kingdom",
  "Japan",
  "Mexico",
  "South Korea",
  "India",
]);

// Preset sector labels; IDs are resolved from API sectors by name so backend data matches (backend CSV may use different IDs than real HS2)
const PRESET_SECTOR_LABELS: { label: string; keywords: string[] }[] = [
  { label: "Auto", keywords: ["auto", "vehicle", "automotive"] },
  { label: "Steel", keywords: ["steel", "metal", "mineral", "iron"] },
  { label: "Lumber", keywords: ["wood", "lumber", "paper"] },
  { label: "Oil", keywords: ["energy", "oil", "fuel", "mineral"] },
  { label: "Agri", keywords: ["agricultural", "agri", "food"] },
  { label: "Tech", keywords: ["electrical", "electronic", "machinery", "optical"] },
];

function resolvePresetSectorId(label: string, keywords: string[], sectors: SectorOption[]): string | null {
  const name = sectors.find((s) =>
    keywords.some((kw) => s.sector_name.toLowerCase().includes(kw))
  );
  return name?.sector_id ?? null;
}

function toBackendPartner(displayName: string): "US" | "China" | "EU" | null {
  if (displayName === "USA") return "US";
  if (displayName === "China") return "China";
  if (EU_COUNTRIES.has(displayName)) return "EU";
  if (UNSUPPORTED_NON_EU.has(displayName)) return null;
  return null;
}

function hasUnsupportedPartner(partnerDisplayNames: string[] | undefined): boolean {
  if (!partnerDisplayNames?.length) return false;
  return partnerDisplayNames.some((name) => UNSUPPORTED_NON_EU.has(name));
}

const DEFAULT_SCENARIO: ScenarioState = {
  tariffPercent: 0,
  targetPartners: ["US"],
  sectorFilter: null,
  partnerDisplayNames: ["USA"],
};

interface ScenarioControlsProps {
  scenario: ScenarioState;
  setScenario: (s: ScenarioState | ((prev: ScenarioState) => ScenarioState)) => void;
  onRun: () => void;
  onLoadBaseline?: () => void;
  presets: ScenarioPreset[];
  onSelectPreset: (preset: ScenarioPreset) => void;
  sectors: SectorOption[];
  partners?: PartnerItem[];
  sectorsLoading?: boolean;
  isRunning?: boolean;
  error?: string | null;
}

export function ScenarioControls({
  scenario,
  setScenario,
  onRun,
  onLoadBaseline,
  presets,
  onSelectPreset,
  sectors,
  partners = [],
  sectorsLoading = false,
  isRunning = false,
  error = null,
}: ScenarioControlsProps) {
  const [mode, setMode] = useState<"preset" | "custom">("preset");
  const [presetId, setPresetId] = useState<string>("");
  const [presetOpen, setPresetOpen] = useState(false);
  const [partnerOpen, setPartnerOpen] = useState(false);
  const [sectorOpen, setSectorOpen] = useState(false);
  const [customPartnerOpen, setCustomPartnerOpen] = useState(false);
  const [customSectorOpen, setCustomSectorOpen] = useState(false);
  const [customPartnerQuery, setCustomPartnerQuery] = useState("");
  const [customPartnerManual, setCustomPartnerManual] = useState("");
  const [customSectorQuery, setCustomSectorQuery] = useState("");


  const hasUnsupported = hasUnsupportedPartner(scenario.partnerDisplayNames);
  const runDisabled = isRunning || scenario.targetPartners.length === 0 || hasUnsupported;

  const handleReset = useCallback(() => {
    setScenario(DEFAULT_SCENARIO);
    setPresetId("");
  }, [setScenario]);

  const handlePresetChange = useCallback(
    (id: string) => {
      setPresetId(id);
      const preset = presets.find((p) => p.id === id);
      if (preset) {
        onSelectPreset(preset);
      }
      setPresetOpen(false);
    },
    [presets, onSelectPreset]
  );

  const selectPartnerByDisplayName = useCallback(
    (displayName: string) => {
      const backend = toBackendPartner(displayName);
      if (backend !== null) {
        setScenario((prev) => ({
          ...prev,
          targetPartners: [backend],
          partnerDisplayNames: [displayName],
        }));
        setPartnerOpen(false);
      } else {
        setScenario((prev) => ({
          ...prev,
          targetPartners: [],
          partnerDisplayNames: [displayName],
        }));
        setPartnerOpen(false);
      }
    },
    [setScenario]
  );

  const openCustomPartner = useCallback(() => {
    setSectorOpen(false);
    setPartnerOpen(false);
    setCustomPartnerOpen(true);
    setCustomPartnerQuery("");
    setCustomPartnerManual("");
  }, []);

  const applyCustomPartner = useCallback(() => {
    const raw = (customPartnerManual.trim() || customPartnerQuery.trim());
    if (!raw) return;
    const normalized = raw.charAt(0).toUpperCase() + raw.slice(1).toLowerCase();
    const displayName = normalized === "Usa" ? "USA" : normalized === "Uk" ? "United Kingdom" : normalized;
    const backend = toBackendPartner(displayName);
    if (backend !== null) {
      setScenario((prev) => ({
        ...prev,
        targetPartners: [backend],
        partnerDisplayNames: [displayName],
      }));
    } else {
      setScenario((prev) => ({
        ...prev,
        targetPartners: [],
        partnerDisplayNames: [displayName],
      }));
    }
    setCustomPartnerOpen(false);
    setCustomPartnerQuery("");
    setCustomPartnerManual("");
  }, [customPartnerManual, customPartnerQuery, setScenario]);

  const selectSector = useCallback(
    (sectorId: string | null) => {
      setScenario((prev) => ({
        ...prev,
        sectorFilter: sectorId === null ? null : [sectorId],
      }));
      setSectorOpen(false);
      setCustomSectorOpen(false);
    },
    [setScenario]
  );

  const openCustomSector = useCallback(() => {
    setPartnerOpen(false);
    setSectorOpen(false);
    setCustomSectorOpen(true);
    setCustomSectorQuery("");
  }, []);

  const filteredSectorsForCustom = useMemo(() => {
    if (!customSectorQuery.trim()) return sectors.slice(0, 30);
    const q = customSectorQuery.toLowerCase();
    return sectors.filter((s) => s.sector_name.toLowerCase().includes(q)).slice(0, 30);
  }, [sectors, customSectorQuery]);

  // Get available sectors (excluding those already in sectorTariffs)
  const usedSectorIds = useMemo(() => {
    return new Set(scenario.sectorTariffs?.map(st => st.sector_id) || []);
  }, [scenario.sectorTariffs]);

  const availableSectors = useMemo(() => {
    return sectors.filter(s => !usedSectorIds.has(s.sector_id));
  }, [sectors, usedSectorIds]);

  // Resolve preset labels to backend sector IDs by name (backend CSV may use different IDs than real HS2)
  const presetSectors = useMemo(() => {
    return PRESET_SECTOR_LABELS.map(({ label, keywords }) => {
      const id = resolvePresetSectorId(label, keywords, sectors);
      return id ? { id, label } : null;
    }).filter((p): p is { id: string; label: string } => p !== null);
  }, [sectors]);

  const sectorLabel =
    scenario.sectorFilter === null || scenario.sectorFilter.length === 0
      ? "All sectors"
      : scenario.sectorFilter.length === 1
        ? (presetSectors.find((p) => p.id === scenario.sectorFilter![0])?.label ??
           sectors.find((s) => s.sector_id === scenario.sectorFilter![0])?.sector_name ??
           scenario.sectorFilter[0])
        : `${scenario.sectorFilter.length} sectors`;

  const partnerLabel = (() => {
    if (scenario.targetPartners.length === 0) {
      if (scenario.partnerDisplayNames?.[0]) return scenario.partnerDisplayNames[0];
      return "—";
    }
    const display = scenario.partnerDisplayNames?.[0];
    if (display && EU_COUNTRIES.has(display)) return `EU (via ${display})`;
    if (scenario.targetPartners[0] === "US" && (!display || display === "USA")) return "USA";
    if (scenario.targetPartners[0] === "China") return "China";
    if (scenario.targetPartners[0] === "EU") return display ? `EU (via ${display})` : "EU";
    return scenario.targetPartners.join(", ");
  })();

  return (
    <div className="space-y-2.5 flex-1 flex flex-col ml-6">
      {/* Controls: Mode, Preset, Tariff %, Partner, Sector, Actions */}
      <div className="flex items-end gap-4 bg-white/[0.02] border border-white/5 rounded-lg px-3 py-2 flex-wrap">
        {/* Mode */}
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wider text-white/40 font-medium mb-0.5">Mode</span>
          <div className="flex rounded-md border border-white/10 overflow-hidden">
            <button
              type="button"
              onClick={() => setMode("preset")}
              className={`px-2.5 py-1.5 text-[11px] font-medium transition-colors ${mode === "preset" ? "bg-white/10 text-white" : "text-white/50 hover:text-white/70"}`}
            >
              Preset
            </button>
            <button
              type="button"
              onClick={() => { setMode("custom"); setPresetOpen(false); }}
              className={`px-2.5 py-1.5 text-[11px] font-medium transition-colors ${mode === "custom" ? "bg-white/10 text-white" : "text-white/50 hover:text-white/70"}`}
            >
              Custom
            </button>
          </div>
        </div>

        <div className="h-4 w-px bg-white/10" />

        {/* Preset */}
        <div className="flex flex-col relative">
          <span className="text-[10px] uppercase tracking-wider text-white/40 font-medium mb-0.5">Preset</span>
          <div className="relative">
            <button
              type="button"
              onClick={() => mode !== "custom" && setPresetOpen((o) => !o)}
              disabled={mode === "custom"}
              className="flex items-center gap-1 bg-white/5 border border-white/10 rounded text-xs text-white/90 font-medium py-1.5 pl-2 pr-6 min-w-[160px] truncate focus:outline-none focus:border-white/20 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {presets.find((p) => p.id === presetId)?.name ?? "Start from preset"}
              <ChevronDown className="w-3 h-3 text-white/50 absolute right-2" />
            </button>
            {presetOpen && mode !== "custom" && (
              <>
                <div className="fixed inset-0 z-10" aria-hidden onClick={() => setPresetOpen(false)} />
                <div className="absolute top-full left-0 mt-1 z-20 bg-[#0f1419] border border-white/10 rounded-md shadow-lg py-1 min-w-[200px] max-h-[320px] overflow-auto">
                  <button
                    type="button"
                    onClick={() => handlePresetChange("")}
                    className="w-full text-left px-3 py-1.5 text-xs text-white/70 hover:bg-white/5"
                  >
                    Start from preset
                  </button>
                  {presets.map((p) => (
                    <button
                      key={p.id}
                      type="button"
                      onClick={() => handlePresetChange(p.id)}
                      className={`w-full text-left px-3 py-1.5 text-xs hover:bg-white/5 flex items-center gap-2 ${presetId === p.id ? "text-white bg-white/5" : "text-white/90"}`}
                    >
                      <span className={`w-2 h-2 rounded-sm shrink-0 ${presetId === p.id ? "bg-blue-500" : "bg-white/20"}`} />
                      {p.name}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        <div className="h-4 w-px bg-white/10" />

        {/* Tariff % */}
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wider text-white/40 font-medium mb-0.5">Tariff %</span>
          <input
            type="number"
            min={0}
            max={25}
            step={0.5}
            value={scenario.tariffPercent}
            onChange={(e) => {
              const v = parseFloat(e.target.value);
              if (!Number.isNaN(v)) setScenario((prev) => ({ ...prev, tariffPercent: Math.max(0, Math.min(25, v)) }));
            }}
            className="w-14 bg-white/5 border border-white/10 rounded text-xs text-white/90 font-mono py-1.5 px-2 focus:outline-none focus:border-white/20"
          />
        </div>

        <div className="h-4 w-px bg-white/10" />

        {/* Partner select */}
        <div className="flex flex-col relative">
          <span className="text-[10px] uppercase tracking-wider text-white/40 font-medium mb-0.5">Partner</span>
          <div className="relative">
            <button
              type="button"
              onClick={() => {
                setSectorOpen(false);
                setCustomPartnerOpen(false);
                setPartnerOpen((o) => !o);
              }}
              className="flex items-center gap-1 bg-white/5 border border-white/10 rounded text-xs text-white/90 font-medium py-1.5 pl-2 pr-6 min-w-[120px] max-w-[180px] truncate focus:outline-none focus:border-white/20"
            >
              {partnerLabel}
              <ChevronDown className="w-3 h-3 text-white/50 absolute right-2" />
            </button>
            {partnerOpen && !customPartnerOpen && (
              <>
                <div className="fixed inset-0 z-10" aria-hidden onClick={() => setPartnerOpen(false)} />
                <div className="absolute top-full left-0 mt-1 z-20 bg-[#0f1419] border border-white/10 rounded-md shadow-lg py-1 min-w-[200px] max-h-[320px] overflow-auto">
                  <div className="px-2 py-1.5 text-[10px] uppercase tracking-wider text-white/40 font-medium">Top partners</div>
                  {partners.length > 0
                    ? partners.map((p) => {
                        const selected = scenario.targetPartners?.[0] === p.id;
                        return (
                          <button
                            key={p.id}
                            type="button"
                            onClick={() => {
                              setScenario((prev) => ({
                                ...prev,
                                targetPartners: [p.id],
                                partnerDisplayNames: [p.name],
                              }));
                              setPartnerOpen(false);
                            }}
                            className="w-full text-left px-3 py-1.5 text-xs hover:bg-white/5 flex items-center gap-2 text-white/90"
                          >
                            <span className={`w-2 h-2 rounded-sm ${selected ? "bg-blue-500" : "bg-white/20"}`} />
                            {p.name}
                          </button>
                        );
                      })
                    : TOP_PARTNERS_DISPLAY.map((name) => {
                        const backend = toBackendPartner(name);
                        const supported = backend !== null;
                        return (
                          <button
                            key={name}
                            type="button"
                            onClick={() => selectPartnerByDisplayName(name)}
                            className={`w-full text-left px-3 py-1.5 text-xs hover:bg-white/5 flex items-center gap-2 ${supported ? "text-white/90" : "text-white/50"}`}
                          >
                            <span className={`w-2 h-2 rounded-sm ${scenario.partnerDisplayNames?.[0] === name ? "bg-blue-500" : "bg-white/20"}`} />
                            {name}
                          </button>
                        );
                      })}
                  <div className="border-t border-white/10 my-1" />
                  <button
                    type="button"
                    onClick={openCustomPartner}
                    className="w-full text-left px-3 py-1.5 text-xs text-white/70 hover:bg-white/5"
                  >
                    Custom…
                  </button>
                </div>
              </>
            )}
        </div>
        {customPartnerOpen && (
          <>
            <div className="fixed inset-0 z-30" aria-hidden onClick={() => setCustomPartnerOpen(false)} />
            <div className="absolute left-0 top-10 z-40 w-72 bg-[#0f1419] border border-white/10 rounded-lg shadow-xl p-3 mt-1">
              <div className="text-[10px] uppercase tracking-wider text-white/40 font-medium mb-2">Custom partner</div>
              <input
                type="text"
                placeholder="Search or type name"
                value={customPartnerQuery}
                onChange={(e) => setCustomPartnerQuery(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded text-xs text-white/90 py-2 px-2.5 focus:outline-none focus:border-white/20 placeholder:text-white/40 mb-2"
              />
              <input
                type="text"
                placeholder="Manual entry (e.g. Germany)"
                value={customPartnerManual}
                onChange={(e) => setCustomPartnerManual(e.target.value)}
                className="w-full bg-white/5 border border-white/10 rounded text-xs text-white/90 py-2 px-2.5 focus:outline-none focus:border-white/20 placeholder:text-white/40 mb-3"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={applyCustomPartner}
                  className="px-3 py-1.5 bg-white/10 text-white text-xs font-medium rounded hover:bg-white/15"
                >
                  Apply
                </button>
                <button
                  type="button"
                  onClick={() => setCustomPartnerOpen(false)}
                  className="px-3 py-1.5 text-white/60 text-xs hover:text-white/80"
                >
                  Cancel
                </button>
              </div>
            </div>
          </>
        )}
      </div>

      {/* Sector select */}
      <div className="flex flex-col relative">
        <span className="text-[10px] uppercase tracking-wider text-white/40 font-medium mb-0.5">Sector</span>
        <div className="relative">
          <button
            type="button"
            onClick={() => {
              if (!sectorsLoading) {
                setPartnerOpen(false);
                setCustomPartnerOpen(false);
                setSectorOpen((o) => !o);
                setCustomSectorOpen(false);
              }
            }}
            disabled={sectorsLoading}
            className="flex items-center gap-1 bg-white/5 border border-white/10 rounded text-xs text-white/90 font-medium py-1.5 pl-2 pr-6 min-w-[140px] max-w-[200px] truncate focus:outline-none focus:border-white/20 disabled:opacity-50"
          >
            {sectorsLoading ? "Loading…" : sectorLabel}
            <ChevronDown className="w-3 h-3 text-white/50 absolute right-2 shrink-0" />
          </button>
          {sectorOpen && !sectorsLoading && !customSectorOpen && (
            <>
              <div className="fixed inset-0 z-10" aria-hidden onClick={() => setSectorOpen(false)} />
              <div className="absolute top-full left-0 mt-1 z-20 bg-[#0f1419] border border-white/10 rounded-md shadow-lg py-1 min-w-[220px] max-h-[320px] overflow-auto">
                <button
                  type="button"
                  onClick={() => selectSector(null)}
                  className="w-full text-left px-3 py-1.5 text-xs text-white/90 hover:bg-white/5"
                >
                  All sectors
                </button>
                <div className="border-t border-white/10 my-1" />
                <div className="px-2 py-1.5 text-[10px] uppercase tracking-wider text-white/40 font-medium">
                  POPULAR SECTORS
                </div>
                {presetSectors.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => selectSector(preset.id)}
                    className="w-full text-left px-3 py-1.5 text-xs text-white/90 hover:bg-white/5"
                  >
                    {preset.label}
                  </button>
                ))}
                <div className="border-t border-white/10 my-1" />
                <div className="px-2 py-1.5 text-[10px] uppercase tracking-wider text-white/40 font-medium">ALL SECTORS</div>
                {sectors.map((s) => (
                  <button
                    key={s.sector_id}
                    type="button"
                    onClick={() => selectSector(s.sector_id)}
                    className="w-full text-left px-3 py-1.5 text-xs text-white/90 hover:bg-white/5 truncate"
                    title={s.sector_name}
                  >
                    {s.sector_name}
                  </button>
                ))}
                <div className="border-t border-white/10 my-1" />
                <button
                  type="button"
                  onClick={openCustomSector}
                  className="w-full text-left px-3 py-1.5 text-xs text-white/70 hover:bg-white/5"
                >
                  Custom…
                </button>
              </div>
            </>
          )}
        </div>
        {customSectorOpen && (
          <>
            <div className="fixed inset-0 z-30" aria-hidden onClick={() => setCustomSectorOpen(false)} />
            <div className="absolute left-0 top-10 z-40 w-80 bg-[#0f1419] border border-white/10 rounded-lg shadow-xl p-3 mt-1">
              <div className="text-[10px] uppercase tracking-wider text-white/40 font-medium mb-2">Custom sector</div>
              <div className="relative mb-2">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/40" />
                <input
                  type="text"
                  placeholder="Search by sector name"
                  value={customSectorQuery}
                  onChange={(e) => setCustomSectorQuery(e.target.value)}
                  className="w-full bg-white/5 border border-white/10 rounded text-xs text-white/90 py-2 pl-8 pr-2.5 focus:outline-none focus:border-white/20 placeholder:text-white/40"
                />
              </div>
              <button
                type="button"
                onClick={() => selectSector(null)}
                className="w-full text-left px-3 py-1.5 text-xs text-white/70 hover:bg-white/5 mb-2"
              >
                All sectors
              </button>
              <div className="max-h-48 overflow-auto">
                {filteredSectorsForCustom.map((s) => (
                  <button
                    key={s.sector_id}
                    type="button"
                    onClick={() => selectSector(s.sector_id)}
                    className="w-full text-left px-3 py-1.5 text-xs text-white/90 hover:bg-white/5 truncate"
                    title={s.sector_name}
                  >
                    {s.sector_name}
                  </button>
                ))}
              </div>
              <button
                type="button"
                onClick={() => setCustomSectorOpen(false)}
                className="mt-2 px-3 py-1.5 text-white/60 text-xs hover:text-white/80"
              >
                Close
              </button>
            </div>
          </>
        )}
      </div>

      <div className="h-4 w-px bg-white/10" />

        {/* Reset */}
        <button
          type="button"
          onClick={handleReset}
          className="p-1.5 text-white/40 hover:text-white transition-colors rounded focus:outline-none focus:ring-1 focus:ring-white/20"
          title="Reset to default (0%, US, All sectors)"
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>

        {/* Baseline (optional) */}
        {onLoadBaseline && (
          <div className="flex flex-col">
            <span className="text-[10px] uppercase tracking-wider text-white/40 font-medium mb-0.5 invisible">Baseline</span>
            <button
              type="button"
              onClick={onLoadBaseline}
              disabled={runDisabled}
              className="flex items-center gap-2 px-3 py-1.5 bg-white/10 hover:bg-white/15 disabled:opacity-50 disabled:cursor-not-allowed text-white/90 text-xs font-medium rounded-md transition-colors"
            >
              {isRunning ? "…" : "Baseline"}
            </button>
          </div>
        )}

        {/* Run */}
        <div className="flex flex-col">
          <span className="text-[10px] uppercase tracking-wider text-white/40 font-medium mb-0.5 invisible">Run</span>
          <button
            type="button"
            onClick={onRun}
            disabled={runDisabled}
            className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-white/10 disabled:text-white/40 text-white text-xs font-semibold rounded-md transition-colors"
          >
            <Play className="w-3 h-3 fill-current" />
            {isRunning ? "Running…" : "RUN SIMULATION"}
          </button>
        </div>
      </div>

      {error && (
        <p className="text-[10px] text-rose-400/90 mt-2 flex-shrink-0">{error}</p>
      )}
    </div>
  );
}
