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

// Color palette untuk slices - gradasi orange (tema dashboard), tetap fixed per posisi kategori
const COLORS = [
  "#F88F22",  // accent-primary
  "#FBB931",  // accent-secondary
  "#EA6113",  // accent-tertiary
  "#c9700f",
  "#FFE3B3",  // accent-soft
  "#a5490a",
  "#ffcf8a",
  "#7a3706",
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

    if (loading)
        return (
            <div className="bg-kpi-card border border-subtle p-6 rounded-lg shadow text-tertiary">
                Loading channel breakdown...
            </div>
        );
    if (error)
        return (
            <div className="bg-red-50 border border-red-200 p-6 rounded-lg text-red-700">
                Error: {error}
            </div>
        );
    if (data.length === 0)
        return (
            <div className="bg-kpi-card border border-subtle p-6 rounded-lg shadow text-tertiary">
                No channel data
            </div>
        );
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
    <div className="bg-kpi-card p-3 border border-subtle rounded-lg hover:bg-card-hover transition-colors shadow h-full flex flex-col min-h-0">
        <h2 className="text-sm font-medium text-secondary mb-1 flex-none">
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
                        stroke="var(--bg-kpi-card)"
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
                        formatter={(value, _name, item) => [
                            `$${Number(value).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                            item.payload.channel,
                        ]}
                        contentStyle={{
                        backgroundColor: "var(--bg-card-hover)",
                        border: "1px solid var(--border-color-strong)",
                        borderRadius: "8px",
                        fontSize: "12px",
                        color: "var(--text-primary)",
                        }}
                        labelStyle={{ color: "var(--text-primary)" }}
                        itemStyle={{ color: "var(--text-secondary)" }}
                    />
                    </PieChart>
                </ResponsiveContainer>

                {/* Center overlay */}
                <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                    <p className="text-base text-primary">
                        ${totalRevenue.toLocaleString()}
                    </p>
                    <p className="text-[10px] text-tertiary uppercase tracking-wide">Total Revenue</p>
                </div>
            </div>
                {/* Legend table */}
                <div className="overflow-y-auto divide-y divide-subtle border border-subtle rounded-lg p-2 shadow-sm">
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
                                    <span className="text-xs text-secondary truncate" title={item.channel}>
                                        {item.channel}
                                    </span>
                                </div>

                                {/* Value */}
                                <span className="text-xs text-primary tabular-nums whitespace-nowrap">
                                    ${item.revenue.toLocaleString()}
                                </span>

                                {/* Percentage */}
                                <span className="text-xs text-tertiary tabular-nums text-right">
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