import { Info, Sparkles } from "lucide-react";
import { cn } from "../../lib/utils";
import type { ScenarioState } from "./ScenarioControls";
import type { ScenarioResult, ScenarioResultSector } from "../../pages/Dashboard";
import type { SectorDetailResponse } from "../../types/api";

interface ExplanationPanelProps {
    scenario?: ScenarioState | null;
    scenarioResult?: ScenarioResult | null;
    sectorDetail?: SectorDetailResponse | null;
    sectorDetailLoading?: boolean;
    selectedSectorId?: string | null;
}

export const ExplanationPanel = ({
    scenario,
    scenarioResult,
    sectorDetail,
    sectorDetailLoading,
    selectedSectorId,
}: ExplanationPanelProps) => {
    const selectedSectorFromResult = selectedSectorId && scenarioResult?.sectors?.length
        ? scenarioResult.sectors.find((s: ScenarioResultSector) => s.sector_id === selectedSectorId)
        : null;
    const explainability = selectedSectorFromResult?.explainability;

    const sectorName = sectorDetail?.sector_name ?? selectedSectorFromResult?.sector_name ?? scenarioResult?.biggest_movers?.[0]?.sector_name ?? "—";
    const partnerShares = sectorDetail?.partner_shares
        ? Object.entries(sectorDetail.partner_shares).sort(([, a], [, b]) => b - a).slice(0, 5)
        : [];

    return (
        <div className="bg-white/[0.02] border border-white/5 rounded-2xl flex flex-col h-full min-h-[400px]">
            <div className="px-5 py-4 border-b border-white/5 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-400" />
                <h3 className="text-sm font-semibold text-white/90">AI Risk Analysis</h3>
            </div>

            <div className="p-5 flex-1 flex flex-col gap-6 overflow-auto">
                {/* Sector / main insight */}
                <div className="space-y-2">
                    <div className="flex items-center gap-2 mb-1">
                        <span className={cn(
                            "px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider border",
                            scenarioResult ? "bg-rose-500/10 text-rose-400 border-rose-500/20" : "bg-white/10 text-white/60 border-white/10"
                        )}>
                            {scenarioResult ? "Live" : "Sample"}
                        </span>
                        <span className="text-xs text-white/40">{sectorName}</span>
                        {sectorDetailLoading && (
                            <span className="text-[10px] text-white/40">Loading…</span>
                        )}
                    </div>
                    <p className="text-sm text-white/80 leading-relaxed">
                        {scenarioResult
                            ? `Risk from ${scenario?.tariffPercent ?? 0}% tariff on ${scenario?.targetPartners?.join(", ") ?? "—"}. Top sector risk: ${scenarioResult.biggest_movers?.[0]?.risk_score?.toFixed(1) ?? "—"}.`
                            : "Run a simulation to see AI risk analysis. Risk increases with exposure to target partners and tariff level."}
                    </p>
                </div>

                {/* Partner shares (from sector detail) */}
                {partnerShares.length > 0 && (
                    <div className="space-y-2">
                        <h4 className="text-xs font-medium text-white/50 uppercase tracking-widest">Partner shares</h4>
                        <div className="space-y-1.5">
                            {partnerShares.map(([partner, share]) => (
                                <div key={partner} className="flex justify-between text-xs text-white/70">
                                    <span>{partner}</span>
                                    <span className="font-mono">{(share * 100).toFixed(1)}%</span>
                                </div>
                            ))}
                        </div>
                        {sectorDetail?.top_partner != null && (
                            <p className="text-[10px] text-white/50">
                                Top partner: {sectorDetail.top_partner} ({(sectorDetail.top_partner_share * 100).toFixed(1)}%)
                            </p>
                        )}
                    </div>
                )}

                {/* Key drivers (explainability from scenario result) */}
                <div className="space-y-3">
                    <h4 className="text-xs font-medium text-white/50 uppercase tracking-widest">Key Drivers</h4>
                    {explainability ? (
                        <div className="space-y-3">
                            <div className="space-y-1">
                                <div className="flex justify-between text-xs text-white/70 mb-1">
                                    <span>Export Exposure</span>
                                    <span className="font-mono">{explainability.exposure_value.toFixed(2)}</span>
                                </div>
                                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-rose-500/60 rounded-full"
                                        style={{ width: `${Math.min(100, explainability.exposure_value * 100)}%` }}
                                    />
                                </div>
                            </div>
                            <div className="space-y-1">
                                <div className="flex justify-between text-xs text-white/70 mb-1">
                                    <span>Concentration</span>
                                    <span className="font-mono">{explainability.concentration_value.toFixed(2)}</span>
                                </div>
                                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                    <div
                                        className="h-full bg-amber-500/60 rounded-full"
                                        style={{ width: `${Math.min(100, explainability.concentration_value * 100)}%` }}
                                    />
                                </div>
                            </div>
                            <div className="text-[10px] text-white/50">
                                Shock: {explainability.shock_value.toFixed(2)} · Exposure component: {explainability.exposure_component.toFixed(2)} · Concentration: {explainability.concentration_component.toFixed(2)}
                            </div>
                        </div>
                    ) : (
                        <>
                            <div className="space-y-1">
                                <div className="flex justify-between text-xs text-white/70 mb-1">
                                    <span>Export Exposure</span>
                                    <span className="font-mono">High</span>
                                </div>
                                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-rose-500/60 w-[85%] rounded-full" />
                                </div>
                            </div>
                            <div className="space-y-1">
                                <div className="flex justify-between text-xs text-white/70 mb-1">
                                    <span>Supply Chain Concentration</span>
                                    <span className="font-mono">Med</span>
                                </div>
                                <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                                    <div className="h-full bg-amber-500/60 w-[60%] rounded-full" />
                                </div>
                            </div>
                        </>
                    )}
                </div>

                {/* Simulation context */}
                <div className="mt-auto pt-4 border-t border-white/5">
                    <div className="flex items-start gap-2 text-xs text-white/50">
                        <Info className="w-3.5 h-3.5 mt-0.5 shrink-0" />
                        <p>Analysis based on 2024 trade data and current simulation parameters. Confidence: High.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};
