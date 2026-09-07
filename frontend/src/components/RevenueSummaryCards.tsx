import { useState, useEffect } from "react";
import axios from "axios";
import KpiList from "./KpiList";
import {
    DollarSign,
    ShoppingCart,
    RotateCcw,
    Package,
    TrendingUp as TrendingUpIcon,
    icons,
} from "lucide-react";

interface SparklinePoint {
    date: string;
    value: string;
}

interface RevenueSummary {
    start_date: string;
    end_date: string;
    total_orders: number;
    net_sales: string;
    total_sales: string;
    total_returns: string;
    average_order_value: string;
    currency: string;
    net_sales_change_percent: string | null;
    total_sales_change_percent: string | null;
    total_returns_change_percent: string | null;
    orders_change_percent: string | null;
    aov_change_percent: string | null;
    net_sales_sparkline: SparklinePoint[];
    total_sales_sparkline: SparklinePoint[];
    total_returns_sparkline: SparklinePoint[];
    orders_sparkline: SparklinePoint[];
    aov_sparkline: SparklinePoint[];
}

// New props
interface RevenueSummaryCardsProps {
    startDate: string;
    endDate: string;
}

function RevenueSummaryCards({ startDate, endDate } : RevenueSummaryCardsProps) {
    const [data, setData] = useState<RevenueSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response =  await axios.get<RevenueSummary>(
                    "http://localhost:8000/api/revenue/summary",
                    {
                        params: {
                            start_date: startDate,
                            end_date: endDate
                        }
                    }
                );
                setData(response.data);
            } catch (err) {
                setError("Failed to fetch summary");
                console.error(err);
            } finally {
                setLoading(false)
            }
        };

        fetchData();
    }, [startDate, endDate]); // refeth if props change

    if (loading) return <p className="bg-white p-6 rounded-lg shadow text-gray-600">Loading Summary ...</p>;
    if (error) return <p className="bg-red-50 border border-red-200 p-6 rounded-lg text-red-700">Error: {error}</p>;
    if (!data) return <p className="bg-white p-6 rounded-lg shadow text-gray-600">No data</p>;

    // Transform sparkline: string values → number
    const toSparklineData = (points: SparklinePoint[]) =>
        points.map((p) => ({value:Number(p.value)}));

    const kpiItems = [
        { 
            label: "Net Sales", 
            value: `$${Number(data.net_sales).toLocaleString()}`,
            changePercent: data.net_sales_change_percent
                ? Number(data.net_sales_change_percent)
                : null,
            icon: <DollarSign size={20} />,
            sparklineData:toSparklineData(data.net_sales_sparkline),
            sparklineColor: "#10b981"
        },
        { 
            label: "Total Sales", 
            value: `$${Number(data.total_sales).toLocaleString()}`,
            changePercent: data.total_sales_change_percent
                ? Number(data.total_sales_change_percent)
                : null,
            icon: <TrendingUpIcon size={20} />,
            sparklineData:toSparklineData(data.total_sales_sparkline),
            sparklineColor: "#10b981"
        },
        { 
            label: "Total Returns", 
            value: `$${Number(data.total_returns).toLocaleString()}`,
            changePercent: data.total_returns_change_percent
                ? Number(data.total_returns_change_percent)
                : null,
            icon: <RotateCcw size={20} />,
            sparklineData: toSparklineData(data.total_returns_sparkline),
            sparklineColor: "#ef4444",  // red
        },
        { 
            label: "Total Orders", 
            value: data.total_orders.toLocaleString(), 
            changePercent: data.orders_change_percent
                ? Number(data.orders_change_percent)
                : null,
            icon: <ShoppingCart size={20} />,
            sparklineData:toSparklineData(data.orders_sparkline),
            sparklineColor: "#10b981"
        },
        { 
            label: "AOV", 
            value: `$${Number(data.average_order_value).toLocaleString()}`,
            changePercent: data.aov_change_percent
                ? Number(data.aov_change_percent)
                : null,
            icon: <ShoppingCart size={20} />,
            sparklineData:toSparklineData(data.aov_sparkline),
            sparklineColor: "#10b981"
        },
    ];

    return (
        <div className="bg-white p-6 rounded-lg shadow space-y-4">
            <div>
            <h2 className="text-xl font-semibold text-gray-900">Revenue Summary</h2>
            <p className="text-sm text-gray-600 mt-1">Period: {data.start_date} to {data.end_date}</p>
            <KpiList items={kpiItems} />
        </div>
        </div>
        
    );
}

export default RevenueSummaryCards;