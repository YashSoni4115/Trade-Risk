import { ArrowUpRight, ArrowDownRight } from "lucide-react";
import { cn } from "../../lib/utils";
import type { ScenarioResult, ScenarioResultSector } from "../../pages/Dashboard";

interface SectorRow {
    id: string;
    name: string;
    risk: number;
    delta: number;
    exposure: string;
}

const mockData: SectorRow[] = [
    { id: "1", name: "Automotive Manufacturing", risk: 85, delta: 12.4, exposure: "US (82%)" },
    { id: "2", name: "Steel & Aluminum", risk: 78, delta: 8.1, exposure: "US (65%)" },
    { id: "3", name: "Softwood Lumber", risk: 62, delta: -2.3, exposure: "US (55%)" },
    { id: "4", name: "Energy (Oil & Gas)", risk: 45, delta: 1.2, exposure: "US (90%)" },
    { id: "5", name: "Agriculture", risk: 30, delta: 0.5, exposure: "Global" },
];

function resultToRows(result: ScenarioResult | null | undefined): SectorRow[] {
    if (!result?.sectors?.length) return mockData;
    const sorted = [...result.sectors].sort((a, b) => (b.risk_delta ?? 0) - (a.risk_delta ?? 0));
    return sorted.slice(0, 20).map((s: ScenarioResultSector) => ({
        id: s.sector_id,
        name: s.sector_name,
        risk: s.risk_score,
        delta: s.risk_delta,
        exposure: `${s.top_partner ?? "—"} (${(s.dependency_percent ?? 0).toFixed(0)}%)`,
    }));
}

interface RiskLeaderboardProps {
    scenarioResult?: ScenarioResult | null;
    onSectorClick?: (sectorId: string) => void;
    selectedSectorId?: string | null;
}

export const RiskLeaderboard = ({ scenarioResult, onSectorClick, selectedSectorId }: RiskLeaderboardProps) => {
    const rows = resultToRows(scenarioResult);
    return (
        <div className="bg-white/[0.02] border border-white/5 rounded-2xl overflow-hidden flex flex-col h-[400px]">
            <div className="px-6 py-4 border-b border-white/5 flex justify-between items-center">
                <h3 className="text-sm font-semibold text-white/90">Sector Risk Ranking</h3>
                <span className="text-xs text-white/40 uppercase tracking-widest">
                    {scenarioResult ? "Live Simulation" : "Mock — run simulation"}
                </span>
            </div>

            <div className="flex-1 overflow-auto">
                <table className="w-full text-left border-collapse">
                    <thead className="bg-white/[0.02] sticky top-0 backdrop-blur-sm z-10">
                        <tr>
                            <th className="px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-widest">Sector</th>
                            <th className="px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-widest text-right">Risk Score</th>
                            <th className="px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-widest text-right">Δ Impact</th>
                            <th className="px-6 py-3 text-xs font-medium text-white/40 uppercase tracking-widest text-right">Top Partner</th>
                        </tr>
                    </thead>
                    <tbody className="divide-y divide-white/5">
                        {rows.map((row) => (
                            <tr
                                key={row.id}
                                onClick={() => onSectorClick?.(row.id)}
                                className={cn(
                                    "hover:bg-white/[0.02] transition-colors group",
                                    onSectorClick ? "cursor-pointer" : "",
                                    selectedSectorId === row.id ? "bg-white/[0.06]" : ""
                                )}
                            >
                                <td className="px-6 py-4 text-sm font-medium text-white/80 group-hover:text-white transition-colors">
                                    {row.name}
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <div className="inline-flex items-center gap-2">
                                        <div className="h-1.5 w-16 bg-white/10 rounded-full overflow-hidden">
                                            <div
                                                className={cn(
                                                    "h-full rounded-full",
                                                    row.risk > 70 ? "bg-rose-500/80" :
                                                        row.risk > 40 ? "bg-amber-500/80" : "bg-emerald-500/80"
                                                )}
                                                style={{ width: `${row.risk}%` }}
                                            />
                                        </div>
                                        <span className="text-sm text-white/70 font-mono">{row.risk}</span>
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-right">
                                    <div className={cn(
                                        "inline-flex items-center gap-1 text-sm font-mono",
                                        row.delta > 0 ? "text-rose-400" : "text-emerald-400"
                                    )}>
                                        {row.delta > 0 ? "+" : ""}{row.delta}%
                                        {row.delta > 0 ? <ArrowUpRight className="w-3 h-3" /> : <ArrowDownRight className="w-3 h-3" />}
                                    </div>
                                </td>
                                <td className="px-6 py-4 text-right text-sm text-white/50">
                                    {row.exposure}
                                </td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
