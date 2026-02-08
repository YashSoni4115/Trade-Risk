import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
} from "recharts";
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
        name: s.sector_name.slice(0, 8),
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

export const PrimaryChart = ({ scenarioResult, baselineResult }: PrimaryChartProps) => {
    const data = resultToChartData(scenarioResult, baselineResult);
    const hasResult = !!scenarioResult?.sectors?.length;
    return (
        <div className="bg-white/[0.02] border border-white/5 rounded-2xl p-5 flex flex-col h-[300px]">
            <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-semibold text-white/90">Risk Distribution Delta</h3>
                {!hasResult && (
                    <span className="text-[10px] text-white/40 uppercase tracking-wider">Run simulation for current settings</span>
                )}
            </div>

            <div className="flex-1 w-full min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={data} barGap={4}>
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
                        <Bar dataKey="baseline" fill="rgba(255,255,255,0.1)" radius={[4, 4, 0, 0]} name="Baseline Risk" />
                        <Bar dataKey="shocked" fill="rgba(244, 63, 94, 0.8)" radius={[4, 4, 0, 0]} name="Shocked Risk" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </div>
    );
};
