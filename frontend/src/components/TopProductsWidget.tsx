import { useState, useEffect } from "react";
import axios from "axios";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";
// import { LineChart, Line, ResponsiveContainer } from "recharts";


interface SparklinePoint {
    date: string;
    revenue: string;
}

interface TopProduct {
    rank: number;
    product_id: number;
    product_name: string;
    revenue: string;
    units_sold: number;
    sparkline: SparklinePoint[];
    previous_revenue: string;
    previous_units_sold: number;
    revenue_change_percent: string | null;
    units_change_percent: string | null;
}

interface TopProductsResponse {
    start_date: string;
    end_date: string;
    products: TopProduct[];
    total_products_count: number;
}

interface TopProductWidgetProps {
    startDate: string;
    endDate: string;
}

function TopProductsWidget({ startDate, endDate }: TopProductWidgetProps) {
    const [data, setData] = useState<TopProductsResponse | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await axios.get<TopProductsResponse>(
                    "http://localhost:8000/api/products/top",
                    {

                        params: {
                            start_date: startDate,
                            end_date: endDate,
                        },
                    }
                );
                setData(response.data);
            } catch (err) {
                setError("Failed to fetch top products");
                console.error(err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [startDate, endDate]);

    if (loading)
        return (
        <div className="bg-white p-6 rounded-lg shadow text-gray-600">
            Loading top products...
        </div>
        );
    if (error)
        return (
        <div className="bg-red-50 border border-red-200 p-6 rounded-lg text-red-700">
            Error: {error}
        </div>
        );
    if (!data || data.products.length === 0)
        return (
        <div className="bg-white p-6 rounded-lg shadow text-gray-600">
            No products data
        </div>
        );
    
    return (
        <div className="bg-white">
            {/* Header */}
            <div className="mb-2">
                <h2 className="text-sm font-semibold text-gray-900">Top Products</h2>
            </div>

            {/* Table */}
            <div className="overflow-auto max-h-96">
                <table className="w-full">
                    <thead className="sticky top-0 bg-white z-10 shadow-sm">
                        <tr className="border-b border-gray-200">
                            <th className="text-left text-[10px] font-medium text-gray-500 uppercase tracking-wide py-1 pr-4 w-12">
                                Rank
                            </th>
                            <th className="text-left text-[10px] font-medium text-gray-500 uppercase tracking-wide py-1 pr-4">
                                Product
                            </th>
                            <th className="text-left text-[10px] font-medium text-gray-500 uppercase tracking-wide py-1 pr-4">
                                Revenue
                            </th>
                            <th className="text-left text-[10px] font-medium text-gray-500 uppercase tracking-wide py-1 pr-4">
                                QTY
                            </th>
                            <th className="text-left text-[10px] font-medium text-gray-500 uppercase tracking-wide py-1 pr-4">
                                QTY Trend
                            </th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.products.map((product) => {
                            // Change indicator setup
                            const changePercent = product.revenue_change_percent
                                ? Number(product.revenue_change_percent)
                                : null;
                            
                            const isPositive = changePercent !== null && changePercent > 0;
                            const isNegative = changePercent !== null && changePercent < 0;
                            const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;
                            const changeColor = isPositive
                                ? "text-green-600"
                                : isNegative
                                ? "text-red-600"
                                : "text-gray-500";

                            return (
                                <tr
                                    key={product.product_id}
                                    className="border-b border-gray-100 hover:bg-gray-50 transition-colors"
                                >
                                    {/* Rank */}
                                    <td className="py-1 pr-4">
                                        <span className="text-xs font-semibold text-gray-500">
                                            #{product.rank}
                                        </span>
                                    </td>

                                    {/* Product Name */}
                                    <td className="py-1 pr-4">
                                        <span className="text-xs font-semibold text-gray-500">
                                            {product.product_name}
                                        </span>
                                    </td>

                                    {/* Revenue */}
                                    <td className="py-1 pr-4">
                                        <span className="text-xs font-semibold text-gray-500">
                                            ${Number(product.revenue).toLocaleString()}
                                        </span>
                                    </td>

                                    {/* Units */}
                                    <td className="py-1 pr-4">
                                        <span className="text-xs font-semibold text-gray-500">
                                            {product.units_sold.toLocaleString()}
                                        </span>
                                    </td>

                                    {/* Change % (NEW) */}
                                    <td className="py-3 pr-4">
                                        {changePercent !== null ? (
                                        <div className={`flex items-center gap-1 text-xs ${changeColor}`}>
                                            <TrendIcon size={14} />
                                            <span className="font-medium">
                                            {isPositive && "+"}
                                            {changePercent.toFixed(1)}%
                                            </span>
                                        </div>
                                        ) : (
                                        <div>
                                            <span className="text-xs text-gray-400 italic">New</span>
                                        </div>
                                        )}
                                    </td>
                                </tr>
                            );
                        })}
                    </tbody>
                </table>
            </div>
        </div>
    );
}

export default TopProductsWidget;