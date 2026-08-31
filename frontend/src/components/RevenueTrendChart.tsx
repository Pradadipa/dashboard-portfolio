import { useState, useEffect } from "react";
import axios from "axios";
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    Tooltip,
    CartesianGrid,
    ResponsiveContainer
} from "recharts"

interface TrendPoint {
    date: string;
    net_sales: string;
    orders: number;
}

interface RevenueTrend {
    start_date: string;
    end_date: string;
    granularity: string;
    data_points: TrendPoint[];
    total_points: number;
}

interface ChartDataPoint {
    date: string;
    netSales: number;
    orders: number;
}

function RevenueTrendChart() {
    const [data, setData] = useState<ChartDataPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response = await axios.get<RevenueTrend>(
                    "http://localhost:8000/api/revenue/trend"
                );
            
            const chartData: ChartDataPoint[] = response.data.data_points.map(
                (point) => ({
                    date: point.date,
                    netSales: Number(point.net_sales),
                    orders: point.orders
                })
            );

            setData(chartData);
            } catch (err) {
                setError("Failed to fetch trend data");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    if (loading) return <p>Loading Chart ...</p>;
    if (error) return <p>Error: {error}</p>;
    if (data.length === 0) return <p>No data available</p>;

    return (
        <div>
            <h2>Revenue Trend</h2>
            <ResponsiveContainer width="100%" height={400}>
                <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip />
                    <Line
                        type="monotone"
                        dataKey="netSales"
                        stroke="#0066cc"
                        strokeWidth={2}
                        name="Net Sales"
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

export default RevenueTrendChart;