import { useState, useEffect } from "react";
import axios from "axios";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    Legend,
    CartesianGrid,
    ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";


interface MonthlyRevenue {
    month: string;
    month_number: number;
    current_year_revenue: string;
    previous_year_revenue: string;
}

interface YearlyRevenueComparisonData {
    current_year: number;
    previous_year: number;
    data: MonthlyRevenue[];
    current_year_total: string;
    previous_year_total: string;
    yoy_change_percent: string | null;
}

interface ChartData {
    month: string;
    currentYear: number;
    previousYear: number;
}

function YearlyRevenueComparison() {
    const [data, setData] = useState<YearlyRevenueComparisonData | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await axios.get<YearlyRevenueComparisonData>(
                    "/api/revenue/yearly-comparison"
                );
                setData(response.data);
            } catch (err) {
                setError("Failed to fetch yearly comparison data");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    if (loading)
        return (
            <div className="bg-kpi-card border border-subtle p-6 rounded-lg shadow text-tertiary">
                Loading yearly comparison...
            </div>
        );
    if (error)
        return (
            <div className="bg-red-50 border border-red-200 p-6 rounded-lg text-red-700">
                Error: {error}
            </div>
        );
    if (!data) return null;

    // Transform Data untuk chart
    const chartData: ChartData[] = data.data.map((month) => ({
        month: month.month,
        currentYear: Number(month.current_year_revenue),
        previousYear: Number(month.previous_year_revenue)
    }));

    // YoY change info
    const yoyChange = data.yoy_change_percent ? Number(data.yoy_change_percent) : null;
    const isPositive = yoyChange !== null && yoyChange > 0;
    const isNegative = yoyChange !== null && yoyChange < 0;
    const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;
    const trendColor = isPositive
        ? "text-green-600"
        : isNegative
        ? "text-red-600"
        : "text-tertiary";

    return (
        <div className="bg-kpi-card p-3 border border-subtle rounded-lg hover:bg-card-hover transition-colors shadow h-full flex flex-col min-h-0">
        {/* Header: Label */}
        <div className="mb-1 flex-none">
                <h2 className="text-sm font-medium text-secondary">
                    Monthly Revenue
                </h2>

            {/* Big Value */}
            <p className="text-lg text-primary">
                ${Number(data.current_year_total).toLocaleString()}
            </p>

            {yoyChange !== null && (
            <div className={`flex items-center gap-1 text-xs ${trendColor} font-medium`}>
                <TrendIcon size={12} />
                <span>
                    {isPositive && "+"}
                    {yoyChange}% YoY
                </span>
                <span className="text-tertiary">
                    vs {data.previous_year}
                </span>
            </div>
            )}
        </div>

        {/* Bar chart */}
        <div className="flex-1 min-h-0">
        <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-color)" />
            <XAxis dataKey="month" stroke="var(--text-tertiary)" tick={{ fontSize: 10, fill: "var(--text-tertiary)" }} />
            <YAxis
                stroke="var(--text-tertiary)"
                tick={{ fontSize: 10, fill: "var(--text-tertiary)" }}
                width={36}
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip
                formatter={(value) => `$${Number(value).toLocaleString()}`}
                contentStyle={{
                    backgroundColor: "var(--bg-card-hover)",
                    border: "1px solid var(--border-color-strong)",
                    borderRadius: "8px",
                    fontSize: 12,
                    color: "var(--text-primary)",
                }}
                labelStyle={{ color: "var(--text-primary)" }}
                itemStyle={{ color: "var(--text-secondary)" }}
            />
            <Legend
                verticalAlign="top"
                align="right"
                wrapperStyle={{ fontSize: 10, color: "var(--text-secondary)" }}
                height={16}
                iconSize={8}
            />
            <Bar
                dataKey="previousYear"
                fill="#cac8c79a"
                opacity={0.2}
                name={`${data.previous_year}`}
                radius={[4, 4, 0, 0]}
            />
            <Bar
                dataKey="currentYear"
                fill="#ff7c10"
                name={`${data.current_year}`}
                radius={[4, 4, 0, 0]}
            />
            </BarChart>
        </ResponsiveContainer>
        </div>
        </div>
    );
}

export default YearlyRevenueComparison;