import { useState, useEffect } from "react";
import axios from "axios";
import {
    Tooltip,
    Pie,
    PieChart,
    ResponsiveContainer,
    Cell,
} from "recharts";


// Create interface data from API
interface ChannelRevenue {
    channel: string;
    orders: number;
    revenue: string;
    percentage: string;
}

interface RevenueByChannel {
    start_date: string;
    end_date: string;
    channels: ChannelRevenue[];
    total_revenue: string;
    total_orders: number;
}

// Create interface for chart (revenue as source)
interface ChartData {
    channel: string;
    revenue: number;
    orders: number;
}

// Create new props for filter date range
interface RevenueByChannelChartProps {
    startDate: string;
    endDate: string;
}

// Color palette untuk slices
const COLORS = [
  "#3b82f6",  // blue
  "#10b981",  // green
  "#f59e0b",  // amber
  "#ef4444",  // red
  "#8b5cf6",  // purple
  "#ec4899",  // pink
  "#14b8a6",  // teal
  "#f97316",  // orange
];

// Create main function
function RevenueByChannelChart({ startDate, endDate }: RevenueByChannelChartProps) {
    const [data, setData] = useState<ChartData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await axios.get<RevenueByChannel>(
                    "http://localhost:8000/api/revenue/by-channel",
                    {
                        params: {
                            start_date: startDate,
                            end_date: endDate
                        }
                    }
                );

                const chartData: ChartData[] = response.data.channels.map((c) => ({
                    channel: c.channel,
                    revenue: Number(c.orders),
                    orders: c.orders
                }));

                setData(chartData);
            } catch (err) {
                setError("Failed to fetch channel data");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [ startDate, endDate ]);

    if (loading) return <p>Loading channel breakdown...</p>;
    if (error) return <p>Error: {error}</p>;
    if (data.length === 0) return <p>No channel data</p>;
    // Hitung total revenue dari data
    const totalRevenue = data.reduce((sum, item) => sum + item.revenue, 0);

    // Hitung percentage per channel
    const dataWithPercentage = data.map((item) => ({
        ...item,
        percentage: totalRevenue > 0 ? (item.revenue/totalRevenue) * 100 : 0,
    }));

    return (
    <div className="bg-white p-3 rounded-lg shadow h-full flex flex-col min-h-0">
        <h2 className="text-sm font-semibold text-gray-900 mb-1 flex-none">
            Revenue by Channel
        </h2>

        {/* Grid: donut kiri, table kanan */}
        <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-2 gap-3 items-center">
            {/* Donut chart */}
            <div className="relative h-full min-h-0">
                <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                    <Pie
                        data={data}
                        dataKey="revenue"
                        nameKey="channel"
                        innerRadius={35}
                        outerRadius={55}
                        paddingAngle={2}
                        cornerRadius={4}
                    >
                        {data.map((_, index) => (
                        <Cell
                            key={`cell-${index}`}
                            fill={COLORS[index % COLORS.length]}
                        />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value) => `$${Number(value).toLocaleString()}`}
                        contentStyle={{
                        backgroundColor: "white",
                        border: "1px solid #e5e7eb",
                        borderRadius: "8px",
                        }}
                    />
                    </PieChart>
                </ResponsiveContainer>

                {/* Center overlay */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <p className="text-sm font-bold text-gray-900">
                        ${totalRevenue.toLocaleString()}
                    </p>
                    <p className="text-[10px] text-gray-500">Total Revenue</p>
                </div>
            </div>
                {/* Legend table */}
                <div className="h-full min-h-0 overflow-y-auto">
                    {dataWithPercentage.map((item, index) => (
                        <div
                            key={item.channel}
                            className="flex items-center justify-between gap-2 py-1">
                                {/* Color dot + name */}
                                <div className="flex items-center gap-2 min-w-0 flex-1">
                                    <div
                                        className="w-2 h-2 rounded-full flex-shrink-0"
                                        style={{ backgroundColor: COLORS[index % COLORS.length]}}
                                        />
                                    <span className="text-xs text-gray-700 truncate">
                                        {item.channel}
                                    </span>
                                </div>

                                {/* Value + percentage */}
                                <div className="flex items-center gap-2 flex-shrink-0">
                                    <span className="text-xs font-medium text-gray-900">
                                        ${item.revenue.toLocaleString()}
                                    </span>
                                    <span className="text-xs text-gray-500 w-12 text-right">
                                        {item.percentage.toFixed(1)}%
                                    </span>
                                </div>
                            </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default RevenueByChannelChart;