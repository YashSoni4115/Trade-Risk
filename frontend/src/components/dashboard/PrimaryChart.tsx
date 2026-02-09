import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, Activity } from "lucide-react";
import type { ScenarioResult, ScenarioResultSector } from "../../pages/Dashboard";

const mockData = [
    { name: "Auto", baseline: 60, shocked: 85 },
    { name: "Steel", baseline: 55, shocked: 78 },
    { name: "Lumber", baseline: 65, shocked: 62 },
    { name: "Oil", baseline: 40, shocked: 45 },
    { name: "Agri", baseline: 30, shocked: 30 },
    { name: "Tech", baseline: 20, shocked: 22 },
];

function resultToChartData(
    result: ScenarioResult | null | undefined,
    baselineResult?: ScenarioResult | null
) {
    if (!result?.sectors?.length) return mockData;
    const baselineMap = new Map<string, number>();
    if (baselineResult?.sectors?.length) {
        for (const b of baselineResult.sectors) {
            baselineMap.set(b.sector_id, b.risk_score);
        }
    }
    return result.sectors.slice(0, 8).map((s: ScenarioResultSector) => ({
        name: s.sector_name,
        baseline: baselineMap.has(s.sector_id)
            ? baselineMap.get(s.sector_id)!
            : Math.max(0, s.risk_score - s.risk_delta),
        shocked: s.risk_score,
    }));
}

interface PrimaryChartProps {
    scenarioResult?: ScenarioResult | null;
    baselineResult?: ScenarioResult | null;
}

// Single sector detailed visualization
const SingleSectorView = ({ sector, baseline }: { sector: ScenarioResultSector; baseline: number }) => {
    const delta = sector.risk_delta;
    const deltaPercent = baseline > 0 ? ((delta / baseline) * 100) : 0;
    const isIncrease = delta > 0;
    
    const getRiskColor = (risk: number) => {
        if (risk > 70) return 'rgb(239, 68, 68)';
        if (risk > 40) return 'rgb(251, 146, 60)';
        return 'rgb(34, 197, 94)';
    };

    const getRiskLevel = (risk: number) => {
        if (risk > 70) return 'CRITICAL';
        if (risk > 50) return 'HIGH';
        if (risk > 30) return 'MODERATE';
        return 'LOW';
    };

    const CircularProgress = ({ value, color }: { value: number; color: string }) => {
        return (
            <div className="relative w-32 h-32 sm:w-40 sm:h-40 lg:w-48 lg:h-48 xl:w-56 xl:h-56">
                <svg className="transform -rotate-90 w-full h-full" viewBox="0 0 220 220">
                    {/* Background circle */}
                    <circle
                        cx="110"
                        cy="110"
                        r="85"
                        stroke="rgba(255,255,255,0.05)"
                        strokeWidth="14"
                        fill="none"
                    />
                    {/* Progress circle */}
                    <circle
                        cx="110"
                        cy="110"
                        r="85"
                        stroke={color}
                        strokeWidth="14"
                        fill="none"
                        strokeDasharray={2 * Math.PI * 85}
                        strokeDashoffset={2 * Math.PI * 85 - (value / 100) * (2 * Math.PI * 85)}
                        strokeLinecap="round"
                        style={{ transition: 'stroke-dashoffset 0.5s ease' }}
                    />
                </svg>
                {/* Center value */}
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className="text-3xl sm:text-4xl lg:text-5xl font-bold text-white mb-0.5 sm:mb-1">
                        {value.toFixed(1)}
                    </span>
                    <span className="text-[9px] sm:text-[10px] lg:text-xs text-white/40 uppercase tracking-widest">
                        Risk Score
                    </span>
                    <span 
                        className="text-[8px] sm:text-[9px] lg:text-[10px] font-semibold mt-1 sm:mt-2 px-1.5 sm:px-2 py-0.5 rounded"
                        style={{ 
                            color: color,
                            backgroundColor: `${color}15`,
                            border: `1px solid ${color}30`
                        }}
                    >
                        {getRiskLevel(value)}
                    </span>
                </div>
            </div>
        );
    };

    // Count available metrics to determine grid layout
    const hasTradeExposure = !!sector.top_partner;
    const hasAffectedValue = sector.affected_export_value !== undefined;
    const hasHHI = sector.concentration !== undefined;
    
    const metricsCount = [hasTradeExposure, hasAffectedValue, hasHHI].filter(Boolean).length;

    return (
        <div className="flex flex-col lg:flex-row items-start gap-4 sm:gap-6">
            {/* Centered Circular Progress */}
            <div className="flex flex-col items-center justify-start flex-shrink-0 w-full lg:w-auto">
                <CircularProgress 
                    value={sector.risk_score} 
                    color={getRiskColor(sector.risk_score)}
                />
                <div className="mt-3 sm:mt-4 text-center px-2">
                    <div className="flex items-center gap-1.5 sm:gap-2 justify-center flex-wrap">
                        {isIncrease ? (
                            <TrendingUp className="w-3 h-3 sm:w-4 sm:h-4 text-rose-400 flex-shrink-0" />
                        ) : (
                            <TrendingDown className="w-3 h-3 sm:w-4 sm:h-4 text-emerald-400 flex-shrink-0" />
                        )}
                        <span className={`text-base sm:text-lg font-bold ${isIncrease ? 'text-rose-400' : 'text-emerald-400'}`}>
                            {isIncrease ? '+' : ''}{delta.toFixed(1)} pts
                        </span>
                        <span className="text-xs sm:text-sm text-white/40 hidden sm:inline">from baseline</span>
                    </div>
                    <div className="text-[10px] sm:text-xs text-white/30 mt-1">
                        Baseline: {baseline.toFixed(1)} → {isIncrease ? '+' : ''}{deltaPercent.toFixed(0)}% change
                    </div>
                </div>
            </div>

            {/* Detailed Information Panel */}
            <div className="flex-1 w-full min-w-0 space-y-2 sm:space-y-3">
                <div className="border-b border-white/5 pb-2 sm:pb-3">
                    <h4 className="text-sm sm:text-base lg:text-lg font-semibold text-white/90 mb-0.5 sm:mb-1 truncate">
                        {sector.sector_name}
                    </h4>
                    <p className="text-[10px] sm:text-xs text-white/40">HS2 Code: {sector.sector_id}</p>
                </div>

                <div className={`grid gap-2 ${metricsCount === 1 ? 'grid-cols-1' : metricsCount === 2 ? 'grid-cols-1 sm:grid-cols-2' : 'grid-cols-1 sm:grid-cols-2 lg:grid-cols-3'}`}>
                    {/* Trade Exposure */}
                    {hasTradeExposure && (
                        <div className="bg-white/[0.03] rounded-lg p-2.5 sm:p-3 border border-white/5">
                            <div className="flex items-center justify-between mb-1.5 sm:mb-2">
                                <span className="text-[9px] sm:text-[10px] lg:text-xs text-white/50 uppercase tracking-wider">
                                    Trade Exposure
                                </span>
                                <Activity className="w-3 h-3 sm:w-3.5 sm:h-3.5 text-white/30 flex-shrink-0" />
                            </div>
                            <div className="flex items-baseline gap-1.5 sm:gap-2 flex-wrap">
                                <span className="text-base sm:text-lg lg:text-xl font-bold text-white/90">
                                    {sector.top_partner}
                                </span>
                                <span className="text-xs sm:text-sm text-white/50">
                                    {(sector.dependency_percent || 0).toFixed(1)}%
                                </span>
                            </div>
                            {sector.dependency_percent !== undefined && (
                                <div className="mt-1.5 sm:mt-2">
                                    <div className="flex justify-between text-[9px] sm:text-xs text-white/40 mb-1">
                                        <span>Dependency</span>
                                        <span>{(sector.dependency_percent * 100).toFixed(0)}%</span>
                                    </div>
                                    <div className="h-1 sm:h-1.5 bg-white/5 rounded-full overflow-hidden">
                                        <div 
                                            className="h-full bg-gradient-to-r from-blue-500 to-purple-500 transition-all duration-500"
                                            style={{ width: `${sector.dependency_percent * 100}%` }}
                                        />
                                    </div>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Export Values */}
                    {hasAffectedValue && (
                        <div className="bg-white/[0.03] rounded-lg p-2.5 sm:p-3 border border-white/5">
                            <div className="space-y-2 sm:space-y-2.5">
                                <div>
                                    <div className="text-[9px] sm:text-[10px] text-white/40 uppercase tracking-wider mb-1">
                                        Affected Value
                                    </div>
                                    <div className="text-base sm:text-lg lg:text-xl font-bold text-rose-400">
                                        ${(sector.affected_export_value! / 1e9).toFixed(2)}B
                                    </div>
                                    <div className="text-[9px] sm:text-xs text-white/50 mt-0.5">Export at risk</div>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* HHI Concentration */}
                    {hasHHI && (
                        <div className="bg-white/[0.03] rounded-lg p-2.5 sm:p-3 border border-white/5">
                            <div className="flex items-center justify-between mb-1.5 sm:mb-2">
                                <span className="text-[9px] sm:text-[10px] lg:text-xs text-white/50 uppercase tracking-wider">
                                    Market Concentration
                                </span>
                                <span className="text-[9px] sm:text-xs text-white/40">HHI</span>
                            </div>
                            <div className="flex items-baseline gap-1.5 sm:gap-2 mb-1.5 sm:mb-2 flex-wrap">
                                <span className="text-base sm:text-lg lg:text-xl font-bold text-white/90">
                                    {(sector.concentration * 10000).toFixed(0)}
                                </span>
                                <span className="text-[10px] sm:text-xs text-white/50">
                                    {sector.concentration > 0.25 ? 'High' : 
                                     sector.concentration > 0.15 ? 'Moderate' : 'Diversified'}
                                </span>
                            </div>
                            <div className="h-1 sm:h-1.5 bg-white/5 rounded-full overflow-hidden">
                                <div 
                                    className={`h-full transition-all duration-500 ${
                                        sector.concentration > 0.25 ? 'bg-rose-500' : 
                                        sector.concentration > 0.15 ? 'bg-amber-500' : 'bg-emerald-500'
                                    }`}
                                    style={{ width: `${Math.min(sector.concentration * 400, 100)}%` }}
                                />
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export const PrimaryChart = ({ scenarioResult, baselineResult }: PrimaryChartProps) => {
    const data = resultToChartData(scenarioResult, baselineResult);
    const hasResult = !!scenarioResult?.sectors?.length;
    const sectorCount = scenarioResult?.sectors?.length || 0;
    const isSingleSector = sectorCount === 1;

    // Single sector detailed view
    if (isSingleSector && scenarioResult?.sectors?.[0]) {
        const sector = scenarioResult.sectors[0];
        const baseline = baselineResult?.sectors?.find(b => b.sector_id === sector.sector_id)?.risk_score 
            || Math.max(0, sector.risk_score - sector.risk_delta);

        return (
            <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-3 sm:p-4 lg:p-6">
                <div className="flex items-center justify-between mb-3 sm:mb-4 lg:mb-6">
                    <h3 className="text-xs sm:text-sm font-semibold text-white/90">Sector Risk Analysis</h3>
                    <span className="text-[8px] sm:text-[10px] text-emerald-400/60 uppercase tracking-wider">
                        LIVE DETAIL VIEW
                    </span>
                </div>
                <SingleSectorView sector={sector} baseline={baseline} />
            </div>
        );
    }
    
    // Multi-sector bar chart (original view)
    return (
        <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-3 sm:p-4 lg:p-5 flex flex-col min-h-[280px] sm:min-h-[320px] lg:h-[360px]">
            <div className="flex items-center justify-between mb-3 sm:mb-4">
                <h3 className="text-xs sm:text-sm font-semibold text-white/90">Risk Distribution Delta</h3>
                {!hasResult && (
                    <span className="text-[8px] sm:text-[10px] text-white/40 uppercase tracking-wider">
                        Run simulation for current settings
                    </span>
                )}
            </div>

            <div className="flex-1 w-full min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} barGap={4} barCategoryGap={sectorCount <= 3 ? "35%" : "20%"}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="rgba(255,255,255,0.05)" />
                        <XAxis
                            dataKey="name"
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
                            dy={10}
                        />
                        <YAxis
                            axisLine={false}
                            tickLine={false}
                            tick={{ fill: 'rgba(255,255,255,0.4)', fontSize: 10 }}
                        />
                        <Tooltip
                            cursor={{ fill: 'rgba(255,255,255,0.02)' }}
                            contentStyle={{
                                backgroundColor: '#0A0A0A',
                                borderColor: 'rgba(255,255,255,0.1)',
                                borderRadius: '8px',
                                fontSize: '12px',
                                color: '#fff'
                            }}
                        />
                        <Bar 
                            dataKey="baseline" 
                            fill="rgba(255,255,255,0.1)" 
                            radius={[4, 4, 0, 0]} 
                            name="Baseline Risk"
                            maxBarSize={sectorCount <= 3 ? 60 : 100}
                        />
                        <Bar 
                            dataKey="shocked" 
                            fill="rgba(244, 63, 94, 0.8)" 
                            radius={[4, 4, 0, 0]} 
                            name="Shocked Risk"
                            maxBarSize={sectorCount <= 3 ? 60 : 100}
                        />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};