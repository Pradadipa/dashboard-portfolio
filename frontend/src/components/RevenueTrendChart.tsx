import { useState, useEffect } from "react";
import axios from "axios";
import {
    AreaChart,
    Area,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid,
    ResponsiveContainer,
    Legend
} from "recharts"
import { TrendingDown, TrendingUp, Minus } from "lucide-react";


interface TrendPoint {
    date: string;
    current_net_sales: string;
    current_orders: number;
    previous_net_sales: string;
    previous_orders: number;
    net_sales_change_percent: string | null;
    orders_change_percent: string | null;
}

interface RevenueTrend {
    start_date: string;
    end_date: string;
    granularity: string;
    data_points: TrendPoint[];
    total_points: number;
    current_total_net_sales: string;
    previous_total_net_sales: string;
    current_total_orders: number;
    previous_total_orders: number;
    net_sales_change_percent: string | null;
    orders_change_percent: string | null;
}

interface ChartDataPoint {
    date: string;
    current: number;
    previous: number;
    changePercent: number | null;
}

interface RevenueTrendChartProps {
    startDate: string;
    endDate: string;
    granularity: string;
}

function RevenueTrendChart({ startDate, endDate, granularity } : RevenueTrendChartProps) {
    const [data, setData] = useState<RevenueTrend | null >(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await axios.get<RevenueTrend>(
                    "http://localhost:8000/api/revenue/trend",
                    {
                        params: {
                            start_date: startDate,
                            end_date: endDate,
                            granularity: granularity
                        }
                    }
                );
            setData(response.data);
            } catch (err) {
                setError("Failed to fetch trend data");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [ startDate, endDate, granularity ]);

    if (loading) 
        return (
            <div className="bg-white p-6 rounded-lg shadow text-gray-600">
                Loading Chart ...
            </div>
        );

    if (error) 
        return (
            <div className="bg-red-50 border border-red-200 p-6 rounded-lg text-red-700">
                Error: {error}
            </div>
        );

    if(!data || data.data_points.length == 0)
        return (
            <div className="bg-white p-6 rounded-lg shadoww text-gray-600">
                No trend data available
            </div>
        );
    
    // Transform for chart
    const chartData: ChartDataPoint[] = data.data_points.map((point) => ({
        date: point.date,
        current: Number(point.current_net_sales),
        previous: Number(point.previous_net_sales),
        changePercent: point.net_sales_change_percent
            ? Number(point.net_sales_change_percent)
            : null
    }));

    // Overall change info
    const overallChange = data.net_sales_change_percent
        ? Number(data.net_sales_change_percent)
        : null;
    const isPositive = overallChange !== null && overallChange > 0;
    const isNegative = overallChange !== null && overallChange < 0;
    const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;
    const trendColor = isPositive
        ? "text-green-600"
        : isNegative
        ? "text-red-600"
        : "text-gray-500"

    return (
        <div className="bg-white p-3 rounded-lg shadow h-full flex flex-col min-h-0">
            {/* Header */}
            <div className="flex-none mb-1">
                <div>
                    <h2 className="text-sm font-semibold text-gray-900">
                        Revenue Trend
                    </h2>
                    {/* <p className="text-sm text-gray-600 mt-1">
                        Current period vs same period last year
                    </p> */}
                </div>

                {/* Big Value */}
                <p className="text-lg font-bold text-gray-900">
                    ${Number(data.current_total_net_sales).toLocaleString()}
                </p>

                {overallChange !== null && (
                    <div className={`flex items-center gap-1 text-xs ${trendColor} font-medium`}>
                        <TrendIcon size={16} />
                        <span>
                            {isPositive && "+"}
                            {overallChange}% YoY
                        </span>
                        <span className="text-gray-500">
                            vs same period last year
                        </span>
                    </div>
                )}
            </div>

            {/* Area Chart */}
            <div className="flex-1 min-h-0">
            <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData} margin={{ top: 4, right: 8, bottom: 0, left: 0 }}>
                    {/* Definisi gradient */}
                    <defs>
                        <linearGradient id="currentGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                            <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                        </linearGradient>
                        <linearGradient id="previousGradient" x1="0" y1="0" x2="0" y2="1">
                            <stop offset="5%" stopColor="#94a3b8" stopOpacity={0.2} />
                            <stop offset="95%" stopColor="#94a3b8" stopOpacity={0} />
                        </linearGradient>
                    </defs>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis
                    dataKey="date"
                    stroke="#6b7280"
                    tick={{ fontSize: 10 }}
                    tickFormatter={(value) => {
                        const date = new Date(value);
                        const day = date.getDate();
                        const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                        const month = months[date.getMonth()];
                        return `${day}-${month}`;
                    }}
                />
                <YAxis
                    stroke="#6b7280"
                    tick={{ fontSize: 10 }}
                    tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                />
                <Tooltip
                    content={({ active, payload }) => {
                    if (!active || !payload || payload.length === 0) return null;

                    const point = payload[0].payload as ChartDataPoint;
                    return (
                        <div className="bg-white border border-gray-200 rounded-lg shadow-lg p-3">
                        <p className="text-sm font-medium text-gray-900 mb-2">
                            {point.date}
                        </p>
                        <div className="space-y-1">
                            <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-blue-500" />
                            <span className="text-xs text-gray-600">Current:</span>
                            <span className="text-sm font-semibold text-gray-900">
                                ${point.current.toLocaleString()}
                            </span>
                            </div>
                            <div className="flex items-center gap-2">
                            <div className="w-3 h-3 rounded-full bg-gray-400" />
                            <span className="text-xs text-gray-600">Previous:</span>
                            <span className="text-sm font-semibold text-gray-700">
                                ${point.previous.toLocaleString()}
                            </span>
                            </div>
                            {point.changePercent !== null && (
                            <div
                                className={`text-xs font-medium mt-2 pt-2 border-t border-gray-100 ${
                                point.changePercent > 0
                                    ? "text-green-600"
                                    : point.changePercent < 0
                                    ? "text-red-600"
                                    : "text-gray-500"
                                }`}
                            >
                                {point.changePercent > 0 && "+"}
                                {point.changePercent}% vs last year
                            </div>
                            )}
                        </div>
                        </div>
                    );
                    }}
                />
                <Legend
                    verticalAlign="top" align="right" wrapperStyle={{ fontSize: 10 }} height={16} iconSize={8}
                />

                {/* Previous area (behind) */}
                <Area
                    type="monotone"
                    dataKey="previous"
                    stroke="#94a3b8"
                    strokeWidth={2}
                    strokeDasharray="5 5"
                    fill="url(#previousGradient)"
                    name="Previous Year"
                />

                {/* Current area (front) */}
                <Area
                    type="monotone"
                    dataKey="current"
                    stroke="#3b82f6"
                    strokeWidth={2}
                    fill="url(#currentGradient)"
                    name="Current Period"
                />
                </AreaChart>
            </ResponsiveContainer>
            </div>
        </div>
    );
}

export default RevenueTrendChart;