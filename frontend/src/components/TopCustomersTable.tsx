import { useState, useEffect } from "react";
import axios from "axios";

// Backend response types
interface TopCustomer {
  rank: number;
  customer_id: number;
  display_name: string | null;
  email_masked: string;
  lifetime_value: string;
  orders_count: number;
  first_purchase_at: string | null;
  last_order_at: string | null;
  days_since_last_order: number;
  country: string | null;
  province: string | null;
  rfm_segment: string;
}

interface TopCustomersResponse {
  total_customers: number;
  limit: number;
  customers: TopCustomer[];
}

// Sunset palette untuk RFM segments (sync dengan CustomerRFMChart)
const SEGMENT_COLORS: Record<string, string> = {
  "Champions": "#F88F22",
  "Loyal": "#FBB931",
  "Cant Lose Them": "#EA6113",
  "At Risk": "#E85D3F",
  "Potential Loyalists": "#F59E0B",
  "Promising": "#FFE3B3",
  "New Customers": "#FDE68A",
  "About to Sleep": "#B88968",
  "Hibernating": "#8B6F52",
  "Lost": "#4A3A2E",
  "Others": "#6B5A47",
};

// Format compact currency
function formatCurrencyCompact(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(1)}k`;
  return `$${value.toFixed(0)}`;
}

// Format location: "California, US" atau fallback
function formatLocation(country: string | null, province: string | null): string {
  if (province && country) return `${province}, ${country}`;
  if (country) return country;
  if (province) return province;
  return "—";
}

// Format days silent dengan context
function formatDaysSilent(days: number): string {
  if (days === 0) return "Today";
  if (days === 1) return "Yesterday";
  if (days < 30) return `${days}d ago`;
  if (days < 365) return `${Math.floor(days / 30)}mo ago`;
  return `${(days / 365).toFixed(1)}yr ago`;
}

interface TopCustomersTableProps {
  limit?: number;
}

function TopCustomersTable({ limit = 10 }: TopCustomersTableProps) {
  const [data, setData] = useState<TopCustomersResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get<TopCustomersResponse>(
          "http://localhost:8000/api/customers/top",
          {
            params: { limit },
          }
        );
        setData(response.data);
      } catch (err) {
        setError("Failed to fetch top customers");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [limit]);

  if (loading)
    return (
      <div className="bg-card p-6 rounded-lg border border-subtle text-secondary">
        Loading top customers...
      </div>
    );

  if (error)
    return (
      <div
        className="bg-card p-6 rounded-lg border border-subtle"
        style={{ color: "var(--color-danger)" }}
      >
        Error: {error}
      </div>
    );

  if (!data || data.customers.length === 0) return null;

  // Hitung total LTV dari top customers (untuk highlight concentration)
  const topLTV = data.customers.reduce(
    (sum, c) => sum + Number(c.lifetime_value),
    0
  );

  return (
    <div className="bg-card p-6 rounded-lg border border-subtle space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-primary">Top Customers</h2>
          <p className="text-sm text-secondary mt-1">
            Highest lifetime value customers · Top {limit} of{" "}
            {data.total_customers.toLocaleString()}
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <p className="text-xs text-tertiary uppercase tracking-wide">
            Top {limit} LTV
          </p>
          <p
            className="text-2xl font-bold tabular-nums"
            style={{ color: "#F88F22" }}
          >
            {formatCurrencyCompact(topLTV)}
          </p>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b-2 border-strong">
              <th className="text-left text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4 w-12">
                #
              </th>
              <th className="text-left text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4">
                Customer
              </th>
              <th className="text-left text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4 w-40">
                Segment
              </th>
              <th className="text-right text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4 w-28">
                Lifetime Value
              </th>
              <th className="text-right text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4 w-20">
                Orders
              </th>
              <th className="text-left text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4 w-40">
                Location
              </th>
              <th className="text-right text-xs font-semibold text-tertiary uppercase tracking-wide py-3 w-28">
                Last Order
              </th>
            </tr>
          </thead>
          <tbody>
            {data.customers.map((customer) => {
              const segmentColor =
                SEGMENT_COLORS[customer.rfm_segment] || "#6B5A47";
              const ltv = Number(customer.lifetime_value);

              // Color urgency Last Order
              const daysColor =
                customer.days_since_last_order > 730
                  ? "var(--color-danger)"
                  : customer.days_since_last_order > 365
                  ? "#FBB931"
                  : "var(--text-primary)";

              return (
                <tr
                  key={customer.customer_id}
                  className="border-b border-subtle hover:bg-card-hover transition-colors"
                >
                  {/* Rank */}
                  <td className="py-3 pr-4">
                    <span className="text-sm font-semibold text-tertiary tabular-nums">
                      #{customer.rank}
                    </span>
                  </td>

                  {/* Customer: name + email */}
                  <td className="py-3 pr-4">
                    <div>
                      <p className="text-sm font-semibold text-primary">
                        {customer.display_name || "Anonymous"}
                      </p>
                      <p className="text-xs text-tertiary mt-0.5 font-mono">
                        {customer.email_masked}
                      </p>
                    </div>
                  </td>

                  {/* RFM Segment badge */}
                  <td className="py-3 pr-4">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-2 h-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: segmentColor }}
                      />
                      <span
                        className="text-xs font-medium px-2 py-1 rounded"
                        style={{
                          backgroundColor: `${segmentColor}15`,
                          color: segmentColor,
                        }}
                      >
                        {customer.rfm_segment}
                      </span>
                    </div>
                  </td>

                  {/* Lifetime Value */}
                  <td className="py-3 pr-4 text-right">
                    <span className="text-sm font-bold text-primary tabular-nums">
                      ${ltv.toLocaleString()}
                    </span>
                  </td>

                  {/* Orders count */}
                  <td className="py-3 pr-4 text-right">
                    <span className="text-sm text-secondary tabular-nums">
                      {customer.orders_count}
                    </span>
                  </td>

                  {/* Location */}
                  <td className="py-3 pr-4">
                    <span className="text-xs text-secondary">
                      {formatLocation(customer.country, customer.province)}
                    </span>
                  </td>

                  {/* Last Order with urgency color */}
                  <td className="py-3 text-right">
                    <span
                      className="text-sm font-medium tabular-nums"
                      style={{ color: daysColor }}
                    >
                      {formatDaysSilent(customer.days_since_last_order)}
                    </span>
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

export default TopCustomersTable;
