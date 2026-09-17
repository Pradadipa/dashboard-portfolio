import { useState, useEffect } from "react";
import axios from "axios";
import KpiList from "./KpiList";
import {
    ShoppingCart,
    TrendingUp as TrendingUpIcon,
    Wallet,
    Shirt,
    CircleStar,
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
    total_qty: number;
    average_order_value: string;
    currency: string;
    net_sales_change_percent: string | null;
    total_sales_change_percent: string | null;
    total_returns_change_percent: string | null;
    orders_change_percent: string | null;
    aov_change_percent: string | null;
    total_qty_change_percent: string | null;
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
            icon: <Wallet size={18} />,
            iconColor: "#F88F22",
            sparklineData:toSparklineData(data.net_sales_sparkline),
            sparklineColor: "#10b981"
        },
        { 
            label: "Gross Sales", 
            value: `$${Number(data.total_sales).toLocaleString()}`,
            changePercent: data.total_sales_change_percent
                ? Number(data.total_sales_change_percent)
                : null,
            icon: <TrendingUpIcon size={18} />,
            iconColor: "#FBB931",
            sparklineData:toSparklineData(data.total_sales_sparkline),
            sparklineColor: "#10b981"
        },
        { 
            label: "Total QTY", 
            value: `${Number(data.total_qty).toLocaleString()}`,
            changePercent: data.total_qty_change_percent
                ? Number(data.total_qty_change_percent)
                : null,
            icon: <Shirt size={18} />,
            iconColor: "#EA6113",
            // sparklineData: toSparklineData(data.total_qty_sparkline),
            sparklineColor: "#ef4444",  // red
        },
        { 
            label: "Total Orders", 
            value: data.total_orders.toLocaleString(), 
            changePercent: data.orders_change_percent
                ? Number(data.orders_change_percent)
                : null,
            icon: <ShoppingCart size={18} />,
            iconColor: "#FFE3B3"
            // sparklineData:toSparklineData(data.orders_sparkline),
            // sparklineColor: "#10b981"
        },
        { 
            label: "AOV", 
            value: `$${Number(data.average_order_value).toLocaleString()}`,
            changePercent: data.aov_change_percent
                ? Number(data.aov_change_percent)
                : null,
            icon: <CircleStar size={18} />,
            iconColor: "#F88F22"
            // sparklineData:toSparklineData(data.aov_sparkline),
            // sparklineColor: "#10b981"
        },
    ];

    return (
        <div className="bg-card p-3 rounded-lg">
            <KpiList items={kpiItems} />
        </div>
    );
}

export default RevenueSummaryCards;