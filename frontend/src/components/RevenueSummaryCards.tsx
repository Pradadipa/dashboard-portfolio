import { useState, useEffect } from "react";
import axios from "axios";
import KpiList from "./KpiList";

interface RevenueSummary {
    start_date: string;
    end_date: string;
    total_orders: number;
    net_sales: string;
    total_sales: string;
    total_returns: string;
    average_order_value: string;
    currency: string;
}

function RevenueSummaryCards() {
    const [data, setData] = useState<RevenueSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const response =  await axios.get<RevenueSummary>(
                    "http://localhost:8000/api/revenue/summary"
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
    }, []);

    if (loading) return <p>Loading Summary ...</p>;
    if (error) return <p>Error: {error}</p>;
    if (!data) return <p>No data</p>;

    const kpiItems = [
        { label: "Net Sales", value: `$${Number(data.net_sales).toLocaleString()}` },
        { label: "Total Sales", value: `$${Number(data.total_sales).toLocaleString()}` },
        { label: "Total Returns", value: `$${Number(data.total_returns).toLocaleString()}` },
        { label: "Total Orders", value: data.total_orders.toLocaleString() },
        { label: "AOV", value: `$${Number(data.average_order_value).toLocaleString()}` },
    ];

    return (
        <div>
            <h2>Revenue Summary</h2>
            <p>Period: {data.start_date} to {data.end_date}</p>
            <KpiList items={kpiItems} />
        </div>
    );
}

export default RevenueSummaryCards;