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
                    "http://localhost:8000/api/revenue/yearly-comparison"
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
            <div className="bg-white p-6 rounded-lg shadow text-gray-600">
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
        : "text-gray-500";

    return (
        <div className="bg-white p-6 rounded-lg shadow">
        {/* Header dengan title dan YoY badge */}
        <div className="flex items-start justify-between mb-4">
            <div>
            <h2 className="text-xl font-semibold text-gray-900">
                Yearly Revenue Comparison
            </h2>
            <p className="text-sm text-gray-600 mt-1">
                {data.previous_year} vs {data.current_year}
            </p>
            </div>

            {yoyChange !== null && (
            <div className={`flex items-center gap-1 text-sm ${trendColor} font-medium`}>
                <TrendIcon size={16} />
                <span>
                {isPositive && "+"}
                {yoyChange}% YoY
                </span>
            </div>
            )}
        </div>

        {/* Bar chart */}
        <ResponsiveContainer width="100%" height={350}>
            <BarChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
            <XAxis dataKey="month" stroke="#6b7280" />
            <YAxis
                stroke="#6b7280"
                tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
            />
            <Tooltip
                formatter={(value) => `$${Number(value).toLocaleString()}`}
                contentStyle={{
                backgroundColor: "white",
                border: "1px solid #e5e7eb",
                borderRadius: "8px",
                }}
            />
            <Legend />
            <Bar
                dataKey="previousYear"
                fill="#777777"
                opacity={0.2}
                name={`${data.previous_year}`}
                radius={[4, 4, 0, 0]}
            />
            <Bar
                dataKey="currentYear"
                fill="#3b82f6"
                name={`${data.current_year}`}
                radius={[4, 4, 0, 0]}
            />
            </BarChart>
        </ResponsiveContainer>
        </div>
    );
}

export default YearlyRevenueComparison;