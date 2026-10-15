import { useState, useEffect } from "react";
import axios from "axios";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

interface CustomerSegmentation {
  start_date: string;
  end_date: string;
  new_customers: number;
  returning_customers: number;
  total_customers: number;
  new_percentage: string;
  returning_percentage: string;
  new_customer_revenue: string;
  returning_customer_revenue: string;
}

interface CustomerSegmentationChartProps {
  startDate: string;
  endDate: string;
}

// Sunset palette: orange + golden untuk 2 segment
const COLORS = ["#F88F22", "#FBB931"];

function CustomerSegmentationChart({ startDate, endDate }: CustomerSegmentationChartProps) {
  const [data, setData] = useState<CustomerSegmentation | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get<CustomerSegmentation>(
          "http://localhost:8000/api/customers/segmentation",
          {
            params: {
              start_date: startDate,
              end_date: endDate,
            },
          }
        );
        setData(response.data);
      } catch (err) {
        setError("Failed to fetch segmentation");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [startDate, endDate]);

  if (loading)
    return (
      <div className="bg-card p-6 rounded-lg border border-subtle text-secondary">
        Loading segmentation...
      </div>
    );
  if (error)
    return (
      <div className="bg-card p-6 rounded-lg border border-subtle" style={{ color: "var(--color-danger)" }}>
        Error: {error}
      </div>
    );
  if (!data) return null;

  // Transform untuk pie chart
  const chartData = [
    {
      name: "New",
      value: data.new_customers,
      revenue: Number(data.new_customer_revenue),
      percentage: Number(data.new_percentage),
    },
    {
      name: "Returning",
      value: data.returning_customers,
      revenue: Number(data.returning_customer_revenue),
      percentage: Number(data.returning_percentage),
    },
  ];

  return (
    <div className="bg-card p-6 rounded-lg border border-subtle">
      <h2 className="text-xl font-semibold text-primary mb-6">
        Customer Segmentation
      </h2>

      {/* Grid 2 kolom: donut kiri, breakdown kanan */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-center">
        {/* KOLOM 1: Donut Chart */}
        <div className="relative">
          <ResponsiveContainer width="100%" height={280}>
            <PieChart>
              <Pie
                data={chartData}
                dataKey="value"
                nameKey="name"
                innerRadius={70}
                outerRadius={110}
                paddingAngle={2}
                cornerRadius={4}
              >
                {chartData.map((_, index) => (
                  <Cell
                    key={`cell-${index}`}
                    fill={COLORS[index % COLORS.length]}
                  />
                ))}
              </Pie>
              <Tooltip
                formatter={(value) => `${Number(value).toLocaleString()} customers`}
                contentStyle={{
                  backgroundColor: "#1c130e",
                  border: "1px solid #2d1810",
                  borderRadius: "8px",
                  color: "#fef3e2",
                }}
              />
            </PieChart>
          </ResponsiveContainer>

          {/* Center overlay: Total Customers */}
          <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
            <p className="text-xl font-bold text-primary tabular-nums">
              {data.total_customers.toLocaleString()}
            </p>
            <p className="text-xs text-secondary mt-1">Total Customers</p>
          </div>
        </div>

        {/* KOLOM 2: Breakdown Cards */}
        <div className="space-y-4">
          {chartData.map((item, index) => (
            <div
              key={item.name}
              className="p-4 rounded-lg border border-subtle"
              style={{ backgroundColor: `${COLORS[index]}10` }}
            >
              {/* Header: name + percentage */}
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div
                    className="w-3 h-3 rounded-full"
                    style={{ backgroundColor: COLORS[index] }}
                  />
                  <span className="text-sm font-semibold text-primary">
                    {item.name} Customers
                  </span>
                </div>
                <span 
                  className="text-sm font-bold tabular-nums" 
                  style={{ color: COLORS[index] }}
                >
                  {item.percentage.toFixed(1)}%
                </span>
              </div>

              {/* Metrics grid: count + revenue */}
              <div className="grid grid-cols-2 gap-4 mt-3">
                <div>
                  <p className="text-xs text-tertiary">Count</p>
                  <p className="text-lg font-bold text-primary tabular-nums">
                    {item.value.toLocaleString()}
                  </p>
                </div>
                <div>
                  <p className="text-xs text-tertiary">Revenue</p>
                  <p className="text-lg font-bold text-primary tabular-nums">
                    ${item.revenue.toLocaleString()}
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

export default CustomerSegmentationChart;
