import { useState, useEffect } from 'react';
import axios from 'axios';
import KpiList from './KpiList';
import {
    Users,
    UserPlus,
    UserCheck,
    TrendingUp,
    Repeat
} from 'lucide-react';

// Create interface for customer metrics
interface CustomerSummary {
    start_date: string;
    end_date: string;
    total_customers: number;
    new_customers: number;
    returning_customers: number;
    average_ltv: string;
    repeat_purchase_rate: string;
    currency: string;
}

// Create interface for CustomerSummaryCards props
interface CustomerSummaryCardsProps {
    startDate: string;
    endDate: string;
}

// Create CustomerSummaryCards component
function CustomerSummaryCards({ startDate, endDate }: CustomerSummaryCardsProps) {
    const [data, setData] = useState<CustomerSummary | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        const fetchData = async () => {
            setLoading(true);
            setError(null);
            try {
                const response = await axios.get<CustomerSummary>(
                    "http://localhost:8000/api/customers/summary",
                    {
                        params: {
                            start_date: startDate,
                            end_date: endDate
                        }
                    }
                );
                setData(response.data);
            } catch (err) {
                setError("Failed to fetch customer summary");
                console.log(err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, [startDate, endDate]);

    if (loading)
        return (
            <div className="bg-card p-6 rounded-lg border border-subtle text-secondary">
                Loading customer summary...
            </div>
        );
    
    if (error)
        return (
            <div 
                className="p-6 rounded-lg border" 
                style={{ 
                backgroundColor: 'var(--color-danger)15', 
                borderColor: 'var(--color-danger)', 
                color: 'var(--color-danger)' 
                }}
            >
                Error: {error}
            </div>
        );
    
    if (!data)
        return (
            <div className="bg-card p-6 rounded-lg border border-subtle text-secondary">
                No data
            </div>
        );
    
    const kpiItems = [
        {
            label: "Total Customers",
            value: data.total_customers.toLocaleString(),
            icon: <Users size={20} />,
            iconColor: "#F88F22",   // sunset bright
        },
        {
            label: "New Customers",
            value: data.new_customers.toLocaleString(),
            icon: <UserPlus size={20} />,
            iconColor: "#FBB931",   // golden
        },
        {
            label: "Returning",
            value: data.returning_customers.toLocaleString(),
            icon: <UserCheck size={20} />,
            iconColor: "#EA6113",   // deep orange
        },
        {
            label: "Avg LTV",
            value: `$${Number(data.average_ltv).toLocaleString()}`,
            icon: <TrendingUp size={20} />,
            iconColor: "#FFE3B3",   // cream
        },
        {
            label: "Repeat Rate",
            value: `${data.repeat_purchase_rate}%`,
            icon: <Repeat size={20} />,
            iconColor: "#F88F22",   // sunset bright
        },
    ];

    return (
        <div className="bg-card p-6 rounded-lg border border-subtle space-y-4">
            <div>
                <h2 className="text-xl font-semibold text-primary">Customer Overview</h2>
                <p className="text-sm text-secondary mt-1">
                    Period: {data.start_date} to {data.end_date}
                </p>
            </div>
            <KpiList items={kpiItems} />
        </div>
    );
}

export default CustomerSummaryCards;