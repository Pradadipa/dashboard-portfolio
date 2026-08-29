import { useState, useEffect } from "react";
import axios from "axios";
import KpiCard from "./components/KpiCard";

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

function App() {
  const [data, setData] = useState<RevenueSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await axios.get<RevenueSummary>(
          'http://localhost:8000/api/revenue/summary'
        );
        setData(response.data);
      } catch (err) {
        setError('Failed to fetch data');
        console.error(err)
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []
);

if (loading) {
  return (
    <div style={{padding: '2rem'}}>
      <h1>Business Dashboard</h1>
      <p>Loading ...</p>
    </div>
  );
}

if (error) {
  return (
      <div style={{ padding: '2rem' }}>
        <h1>Business Dashboard</h1>
        <p style={{ color: 'red' }}>{error}</p>
      </div>
    );
}

return (
  <div>
    <h1>Business Dashboard</h1>
    <p>Period</p>

    <hr />
    <h2>KPIs</h2>
    <ul>
      <KpiCard
        label="Net Sales"
        value={`$${Number(data?.net_sales).toLocaleString()}`}
        />
      <KpiCard
        label="Total Sales"
        value={`$${Number(data?.total_sales).toLocaleString()}`}
        />
      <KpiCard
        label="Total Returns"
        value={`$${Number(data?.total_returns).toLocaleString()}`}
        />
      <KpiCard
        label="Total Orders"
        value={data?.total_orders.toLocaleString() ?? "0"}
        />
      <KpiCard
        label="Average Order Value"
        value={`$${Number(data?.average_order_value).toLocaleString()}`}
        />
    </ul>
  </div>
);
}

export default App;