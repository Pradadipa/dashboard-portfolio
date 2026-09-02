import { useState, useEffect } from "react";
import axios from "axios";
import {
    BarChart,
    Bar,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid,
    ResponsiveContainer,
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

    return (
        <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Revenue by Channel</h2>
            <ResponsiveContainer width="100%" height={400}>
            <BarChart data={data} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis type="number" stroke="#6b7280" />
                <YAxis dataKey="channel" type="category" width={150} stroke="#6b7280" />
                <Tooltip 
                    formatter={(value) => `$${Number(value).toLocaleString()}`}
                contentStyle={{
                    backgroundColor: 'white',
                    border: '1px solid #e5e7eb',
                    borderRadius: '8px',
                }}
                />
                <Bar dataKey="revenue" fill="#1a1a1a" name="Revenue" />
            </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

export default RevenueByChannelChart;