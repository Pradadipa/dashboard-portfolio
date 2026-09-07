import { TrendingUp, TrendingDown, Minus } from "lucide-react";
import { ResponsiveContainer } from "recharts";
import { Area, AreaChart } from 'recharts';
import type { ReactNode } from "react"

interface SparklineData {
    value: number;
}

interface KpiCardProps {
    label: string;
    value: string;
    changePercent?: number | null;
    icon?: ReactNode;
    sparklineData?: SparklineData[];
    sparklineColor?: string;
}

function KpiCard({ 
    label, 
    value,
    changePercent,
    icon,
    sparklineData,
    sparklineColor
} : KpiCardProps) {
    // Determine trend direction
    const isPositive = changePercent !== null && changePercent !== undefined && changePercent > 0;
    const isNegative = changePercent !== null && changePercent !== undefined && changePercent < 0;
    const isNeutral = changePercent === 0;
    const hasChange = changePercent !== null && changePercent !==undefined;

    // Color for change indicator
    const changeColor = isPositive
        ? "text-green-600"
        : isNegative
        ? "text-red-600"
        : "text-gray-500";
    
    // Icon for trend
    const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;

    return (
        <div className="bg-white p-5 rounded-lg shadow border border-gray-100 hover:shadow-md transition-shadow">
            {/* Header: label + icon */}
            <div className="flex items-start justify-between mb-3">
                <p className="text-sm font-medium text-gray-600">{label}</p>
                {icon && (
                    <div className="text-gray-400">
                        {icon}
                    </div>
                )}
            </div>

            {/* Big Value */}
            <p className="text-2xl font-bold text-gray-900 mb-2">{value}</p>

            {/* Change indicator */}
            {hasChange ?(
                <div className={`flex items-center gap-1 text-sm ${changeColor}`}>
                    <TrendIcon size={16} />
                    <span className="font-medium">
                        {isPositive && "+"}
                        {changePercent}%
                    </span>
                    <span className="text-gray-500">vs previous period</span>
                </div>
            ) : (
                <div className="text-sm text-gray-400">No comparison data</div>
            )}

            {/* Sparkline */}
            {sparklineData && sparklineData.length > 0 && (
                <div className="mt-3 h-12">
                    <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={sparklineData} margin={{ top: 2, right: 0, bottom: 0, left: 0 }}>
                            <Area
                                type="monotone"
                                dataKey="value"
                                stroke={sparklineColor}
                                strokeWidth={2}
                                fill={sparklineColor}
                                fillOpacity={0.15}
                                dot={false}
                                isAnimationActive={true}
                            />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            )}
        </div>
    );
}

export default KpiCard;