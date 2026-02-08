import { TrendingUp, DollarSign, Activity } from "lucide-react";
import { cn } from "../../lib/utils";
import type { ScenarioState } from "./ScenarioControls";
import type { ScenarioResult, ScenarioResultSector } from "../../pages/Dashboard";

interface KpiCardProps {
    label: string;
    value: string | number;
    change?: string;
    positive?: boolean;
    icon?: React.ReactNode;
}

const KpiCard = ({ label, value, change, positive, icon }: KpiCardProps) => {
    return (
        <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-4 flex flex-col justify-between h-24 relative overflow-hidden group hover:bg-white/[0.04] transition-colors">
            <div className="absolute top-0 right-0 p-3 opacity-10 group-hover:opacity-20 transition-opacity">
                {icon}
            </div>
            <span className="text-xs uppercase tracking-widest text-white/50 font-medium z-10">
                {label}
            </span>
            <div className="flex items-baseline gap-2 z-10">
                <span className="text-2xl font-semibold text-white/90">{value}</span>
                {change && (
                    <span
                        className={cn(
                            "text-xs font-medium",
                            positive ? "text-emerald-400" : "text-rose-400"
                        )}
                    >
                        {change}
                    </span>
                )}
            </div>
        </div>
    );
};

interface KpiStripProps {
    scenario?: ScenarioState | null;
    scenarioResult?: ScenarioResult | null;
}

export const KpiStrip = ({ scenario, scenarioResult }: KpiStripProps) => {
    const activeLabel = scenario
        ? `${scenario.targetPartners.join(", ")} / ${scenario.tariffPercent}%`
        : "—";
    const topSector = scenarioResult?.biggest_movers?.[0] ?? scenarioResult?.sectors?.[0];
    const largestDelta = scenarioResult?.sectors?.length
        ? Math.max(...scenarioResult.sectors.map((s: ScenarioResultSector) => s.risk_delta))
        : null;
    const totalAffected = scenarioResult?.sectors?.reduce((sum: number, s: ScenarioResultSector) => sum + (s.affected_export_value ?? 0), 0) ?? 0;
    const formatB = (v: number) => (v >= 1e9 ? `${(v / 1e9).toFixed(1)}B` : v >= 1e6 ? `${(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${(v / 1e3).toFixed(1)}k` : String(v));

    return (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <KpiCard
                label="Most Exposed Sector"
                value={topSector?.sector_name ?? "—"}
                icon={<Activity className="w-8 h-8" />}
            />
            <KpiCard
                label="Largest Risk Δ"
                value={largestDelta != null ? `${largestDelta > 0 ? "+" : ""}${largestDelta.toFixed(1)}%` : "—"}
                change="vs Baseline"
                positive={false}
                icon={<TrendingUp className="w-8 h-8" />}
            />
            <KpiCard
                label="Affected Export Value"
                value={totalAffected > 0 ? `$${formatB(totalAffected)}` : "—"}
                icon={<DollarSign className="w-8 h-8" />}
            />
            <KpiCard
                label="Active Scenario"
                value={activeLabel}
                change={scenarioResult ? "Live" : "Set & run"}
                positive={true}
                icon={<Activity className="w-8 h-8" />}
            />
        </div>
    );
};
