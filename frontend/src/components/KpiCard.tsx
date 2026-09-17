import { TrendingUp, TrendingDown, Minus } from "lucide-react";
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
    iconColor?: string;
    sparklineColor?: string;
}

function KpiCard({ 
    label, 
    value,
    changePercent,
    icon,
    iconColor,
} : KpiCardProps) {
    // Determine trend direction
    const isPositive = changePercent !== null && changePercent !== undefined && changePercent > 0;
    const isNegative = changePercent !== null && changePercent !== undefined && changePercent < 0;
    // const isNeutral = changePercent === 0;
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
        <div className="bg-kpi-card p-3 rounded-lg border border-subtle hover:bg-card-hover transition-colors">
        {/* Grid 2 kolom: content + icon */}
        <div className="grid grid-cols-[1fr_auto] gap-3">
            {/* Kolom 1: Content */}
            <div className="min-w-0">
                <p className="text-sm font-medium text-secondary truncate">{label}</p>
                <p className="text-lg text-primary mt-1">{value}</p>
                
                {hasChange ? (
                <div className={`flex items-center gap-1 text-[12px] whitespace-nowrap mt-1 ${changeColor}`}>
                    <TrendIcon size={12} />
                    <span className="font-medium">
                    {isPositive && "+"}
                    {changePercent}%
                    </span>
                    <span className="text-tertiary">vs prev.</span>
                </div>
                ) : (
                <div className="text-[12px] text-tertiary mt-1">No comparison data</div>
                )}
            </div>

            {/* Kolom 2: Icon */}
            {icon && (
                <div className="w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0"
                style={{
                    backgroundColor: `${iconColor || 'var(--accent-primary)'}20`,
                    color: iconColor || 'var(--accent-primary)',
                    boxShadow: `0 0 20px ${iconColor || 'var(--accent-primary)'}20`
                }}>
                {icon}
                </div>
            )}
            
            </div>

            {/* Sparkline */}
            {/* {sparklineData && sparklineData.length > 0 && (
                <div className="mt-1 h-8">
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
            )} */}
        </div>
    );
}

export default KpiCard;