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

interface RevenueTrendChartProps {
    startDate: string;
    endDate: string;
    granularity: string;
}

function RevenueTrendChart({ startDate, endDate, granularity } : RevenueTrendChartProps) {
    const [data, setData] = useState<ChartDataPoint[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
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
    }, [ startDate, endDate, granularity ]);

    if (loading) return <div className="bg-white p-6 rounded-lg shadow text-gray-600">Loading Chart ...</div>
    if (error) return <div className="bg-red-50 border border-red-200 p-6 rounded-lg text-red-700">Error: {error}</div>;
    if (data.length === 0) return <div className="bg-white p-6 rounded-lg shadow text-gray-600">No data available</div>;

    return (
        <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Revenue Trend</h2>
            <ResponsiveContainer width="100%" height={400}>
                <LineChart data={data}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#e0e0e0"/>
                    <XAxis dataKey="date" />
                    <YAxis />
                    <Tooltip contentStyle={{backgroundColor: 'white', border: '0.5px solid #dfdbdb', borderRadius: '8px'}} />
                    <Line
                        type="monotone"
                        dataKey="netSales"
                        stroke="#1a1a1a"
                        strokeWidth={2}
                        name="Net Sales"
                    />
                </LineChart>
            </ResponsiveContainer>
        </div>
    );
}

export default RevenueTrendChart;