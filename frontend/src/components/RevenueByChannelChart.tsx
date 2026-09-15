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

// Color palette untuk slices - fixed categorical order (CVD-safe), never cycled/reassigned by rank
const COLORS = [
  "#2a78d6",  // blue
  "#eb6834",  // orange
  "#1baf7a",  // aqua
  "#eda100",  // yellow
  "#e87ba4",  // magenta
  "#008300",  // green
  "#4a3aa7",  // violet
  "#e34948",  // red
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
                    revenue: Number(c.revenue),
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

    // Color tetap terikat ke channel (bukan posisi/rank) supaya donut & legend selalu konsisten
    const colorByChannel = new Map(
        data.map((item, index) => [item.channel, COLORS[index % COLORS.length]])
    );

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
                        innerRadius="55%"
                        outerRadius="92%"
                        paddingAngle={2}
                        cornerRadius={4}
                        stroke="#fcfcfb"
                        strokeWidth={2}
                    >
                        {data.map((item) => (
                        <Cell
                            key={`cell-${item.channel}`}
                            fill={colorByChannel.get(item.channel)}
                        />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value: number, _name, item) => [
                            `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                            item.payload.channel,
                        ]}
                        contentStyle={{
                        backgroundColor: "white",
                        border: "1px solid #e5e7eb",
                        borderRadius: "8px",
                        fontSize: "12px",
                        }}
                    />
                    </PieChart>
                </ResponsiveContainer>

                {/* Center overlay */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <p className="text-base font-bold text-gray-900">
                        ${totalRevenue.toLocaleString()}
                    </p>
                    <p className="text-[10px] text-gray-500 uppercase tracking-wide">Total Revenue</p>
                </div>
            </div>
                {/* Legend table */}
                <div className="overflow-y-auto divide-y divide-gray-100 border border-gray-100 rounded-lg p-2 shadow-sm">
                    {[...dataWithPercentage]
                        .sort((a, b) => b.revenue - a.revenue)
                        .map((item) => (
                        <div
                            key={item.channel}
                            className="grid grid-cols-[1fr_auto_2.5rem] items-center gap-3 py-1.5">
                                {/* Color dot + name */}
                                <div className="flex items-center gap-2 min-w-0">
                                    <span
                                        className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                                        style={{ backgroundColor: colorByChannel.get(item.channel) }}
                                        />
                                    <span className="text-xs text-gray-700 truncate" title={item.channel}>
                                        {item.channel}
                                    </span>
                                </div>

                                {/* Value */}
                                <span className="text-xs font-medium text-gray-900 tabular-nums whitespace-nowrap">
                                    ${item.revenue.toLocaleString()}
                                </span>

                                {/* Percentage */}
                                <span className="text-xs text-gray-500 tabular-nums text-right">
                                    {item.percentage.toFixed(1)}%
                                </span>
                            </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export default RevenueByChannelChart;