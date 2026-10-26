import { useState, useEffect } from "react";
import axios from "axios";

// Backend response types
interface RFMSegment {
  segment: string;
  customer_count: number;
  avg_lifetime_value: string;
  total_lifetime_value: string;
  avg_orders: string;
  avg_days_since_order: number;
  percentage: string;
}

interface CustomerRFM {
  reference_date: string;
  total_active_customers: number;
  segments: RFMSegment[];
}

interface SegmentRow {
  name: string;
  count: number;
  avgLtv: number;
  totalLtv: number;
  avgOrders: number;
  avgDays: number;
  percentage: number;
  color: string;
  description: string;
}

const SEGMENT_CONFIG: Record<string, { color: string; description: string }> = {
  "Champions": {
    color: "#F88F22",
    description: "Best customers — VIP program, early access",
  },
  "Loyal": {
    color: "#FBB931",
    description: "Still active, frequent — Upsell premium",
  },
  "Cant Lose Them": {
    color: "#EA6113",
    description: "Churning VIPs — Urgent personal outreach",
  },
  "At Risk": {
    color: "#E85D3F",
    description: "Was valuable, disappearing — Win-back campaign",
  },
  "Potential Loyalists": {
    color: "#F59E0B",
    description: "Nurture ke Loyal — 3rd order incentive",
  },
  "Promising": {
    color: "#FFE3B3",
    description: "Encourage repeat — Product recommendations",
  },
  "New Customers": {
    color: "#FDE68A",
    description: "Welcome series, educate — 2nd purchase incentive",
  },
  "About to Sleep": {
    color: "#B88968",
    description: "Personalized recs based on history",
  },
  "Hibernating": {
    color: "#8B6F52",
    description: "Low priority — Occasional broadcast",
  },
  "Lost": {
    color: "#4A3A2E",
    description: "Deprioritize or final win-back attempt",
  },
  "Others": {
    color: "#6B5A47",
    description: "Mixed signals — Default engagement",
  },
};

// Format: $34.4M, $5.8M, $245k, etc.
function formatCurrencyCompact(value: number): string {
  if (value >= 1_000_000) return `$${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `$${(value / 1_000).toFixed(0)}k`;
  return `$${value.toFixed(0)}`;
}

function CustomerRFMChart() {
  const [data, setData] = useState<CustomerRFM | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get<CustomerRFM>(
          "http://localhost:8000/api/customers/rfm"
        );
        setData(response.data);
      } catch (err) {
        setError("Failed to fetch RFM data");
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, []);

  if (loading)
    return (
      <div className="bg-card p-6 rounded-lg border border-subtle text-secondary">
        Loading RFM segmentation...
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

  if (!data) return null;

  // Transform data untuk table
  const rows: SegmentRow[] = data.segments.map((seg) => {
    const config = SEGMENT_CONFIG[seg.segment] || {
      color: "#6B5A47",
      description: "",
    };
    return {
      name: seg.segment,
      count: seg.customer_count,
      avgLtv: Number(seg.avg_lifetime_value),
      totalLtv: Number(seg.total_lifetime_value),
      avgOrders: Number(seg.avg_orders),
      avgDays: seg.avg_days_since_order,
      percentage: Number(seg.percentage),
      color: config.color,
      description: config.description,
    };
  });

  // Hitung aggregates untuk header
  const totalLTV = rows.reduce((sum, s) => sum + s.totalLtv, 0);
  const maxPercentage = Math.max(...rows.map((r) => r.percentage));

  // Hitung total value top 3 segments (Champions, Loyal, Cant Lose Them)
  const topSegmentsLTV = rows
    .filter((r) => ["Champions", "Loyal", "Cant Lose Them"].includes(r.name))
    .reduce((sum, r) => sum + r.totalLtv, 0);
  const topSegmentsPct = (topSegmentsLTV / totalLTV) * 100;

  return (
    <div className="bg-card p-6 rounded-lg border border-subtle space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <h2 className="text-xl font-semibold text-primary">
            Customer Segmentation (RFM)
          </h2>
          <p className="text-sm text-secondary mt-1">
            Recency × Frequency × Monetary — 10 segments based on lifetime behavior
          </p>
        </div>

        {/* KPI mini cards di header */}
        <div className="flex gap-4 flex-wrap">
          <div className="text-right">
            <p className="text-xs text-tertiary uppercase tracking-wide">
              Active Customers
            </p>
            <p className="text-2xl font-bold text-primary tabular-nums">
              {data.total_active_customers.toLocaleString()}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-tertiary uppercase tracking-wide">
              Total LTV
            </p>
            <p
              className="text-2xl font-bold tabular-nums"
              style={{ color: "#F88F22" }}
            >
              {formatCurrencyCompact(totalLTV)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-tertiary uppercase tracking-wide">
              Top 3 Segments
            </p>
            <p
              className="text-2xl font-bold tabular-nums"
              style={{ color: "#FBB931" }}
            >
              {topSegmentsPct.toFixed(1)}%
            </p>
            <p className="text-xs text-tertiary mt-0.5">of revenue</p>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b-2 border-strong">
              <th className="text-left text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4">
                Segment
              </th>
              <th className="text-right text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4 w-32">
                Customers
              </th>
              <th className="text-left text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4 w-44">
                Distribution
              </th>
              <th className="text-right text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4">
                Avg LTV
              </th>
              <th className="text-right text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4">
                Total LTV
              </th>
              <th className="text-right text-xs font-semibold text-tertiary uppercase tracking-wide py-3 pr-4 w-24">
                Avg Orders
              </th>
              <th className="text-right text-xs font-semibold text-tertiary uppercase tracking-wide py-3 w-32">
                Days Silent
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => {
              // Normalize percentage ke 0-100 range (relative ke max segment)
              const barWidth = (row.percentage / maxPercentage) * 100;

              // Color-code days silent
              const daysColor =
                row.avgDays > 730
                  ? "var(--color-danger)"
                  : row.avgDays > 365
                  ? "#FBB931"
                  : "var(--text-primary)";

              return (
                <tr
                  key={row.name}
                  className="border-b border-subtle hover:bg-card-hover transition-colors"
                >
                  {/* Segment: color dot + name + description */}
                  <td className="py-4 pr-4">
                    <div className="flex items-center gap-3">
                      <div
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{ backgroundColor: row.color }}
                      />
                      <div>
                        <p className="text-sm font-semibold text-primary">
                          {row.name}
                        </p>
                        <p className="text-xs text-tertiary mt-0.5 max-w-md">
                          {row.description}
                        </p>
                      </div>
                    </div>
                  </td>

                  {/* Customers count */}
                  <td className="py-4 pr-4 text-right">
                    <p className="text-sm font-semibold text-primary tabular-nums">
                      {row.count.toLocaleString()}
                    </p>
                    <p className="text-xs text-tertiary tabular-nums mt-0.5">
                      {row.percentage.toFixed(2)}%
                    </p>
                  </td>

                  {/* Distribution: progress bar */}
                  <td className="py-4 pr-4">
                    <div
                      className="w-full h-2 rounded-full overflow-hidden"
                      style={{ backgroundColor: "var(--border-color)" }}
                    >
                      <div
                        className="h-full rounded-full transition-all"
                        style={{
                          width: `${barWidth}%`,
                          backgroundColor: row.color,
                        }}
                      />
                    </div>
                  </td>

                  {/* Avg LTV */}
                  <td className="py-4 pr-4 text-right">
                    <span className="text-sm font-semibold text-primary tabular-nums">
                      ${row.avgLtv.toLocaleString()}
                    </span>
                  </td>

                  {/* Total LTV */}
                  <td className="py-4 pr-4 text-right">
                    <span className="text-sm text-secondary tabular-nums">
                      {formatCurrencyCompact(row.totalLtv)}
                    </span>
                  </td>

                  {/* Avg Orders */}
                  <td className="py-4 pr-4 text-right">
                    <span className="text-sm text-secondary tabular-nums">
                      {row.avgOrders}
                    </span>
                  </td>

                  {/* Days Silent with color coding */}
                  <td className="py-4 text-right">
                    <span
                      className="text-sm font-medium tabular-nums"
                      style={{ color: daysColor }}
                    >
                      {row.avgDays}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
          {/* Footer with totals */}
          <tfoot>
            <tr className="border-t-2 border-strong">
              <td className="py-3 pr-4">
                <p className="text-sm font-bold text-primary">Total</p>
              </td>
              <td className="py-3 pr-4 text-right">
                <p className="text-sm font-bold text-primary tabular-nums">
                  {data.total_active_customers.toLocaleString()}
                </p>
                <p className="text-xs text-tertiary">100%</p>
              </td>
              <td className="py-3 pr-4"></td>
              <td className="py-3 pr-4 text-right"></td>
              <td className="py-3 pr-4 text-right">
                <p className="text-sm font-bold text-primary tabular-nums">
                  {formatCurrencyCompact(totalLTV)}
                </p>
              </td>
              <td className="py-3 pr-4"></td>
              <td className="py-3"></td>
            </tr>
          </tfoot>
        </table>
      </div>
    </div>
  );
}

export default CustomerRFMChart;
