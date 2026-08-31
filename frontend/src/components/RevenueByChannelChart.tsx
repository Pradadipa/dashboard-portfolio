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

// Create main function
function RevenueByChannelChart() {
    const [data, setData] = useState<ChartData[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await axios.get<RevenueByChannel>(
                    "http://localhost:8000/api/revenue/by-channel"
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
    }, []);

    if (loading) return <p>Loading channel breakdown...</p>;
    if (error) return <p>Error: {error}</p>;
    if (data.length === 0) return <p>No channel data</p>;

    return (
        <div>
            <h2>Revenue by Channel</h2>
            <ResponsiveContainer width="100%" height={400}>
                <BarChart data={data} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis type="number" />
                    <YAxis dataKey="channel" type="category" width={150} />
                    <Tooltip formatter={(value) => `$${Number(value).toLocaleString()}`} />
                    <Bar dataKey="revenue" fill="#0066cc" name="Revenue" />
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
}

export default RevenueByChannelChart;