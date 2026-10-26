import { useState, useEffect } from "react";
import axios from "axios";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ResponsiveContainer,
} from "recharts";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

interface AcquisitionTrendPoint {
  month: string;
  new_customers: number;
  returning_customers: number;
  total_active: number;
  repeat_rate_percent: string;
}

interface AcquisitionTrend {
  start_month: string;
  end_month: string;
  data_points: AcquisitionTrendPoint[];
  total_new: number;
  total_returning: number;
  current_month_total: number;
  mom_change_percent: string | null;
  current_repeat_rate: string;
}

interface ChartDataPoint {
  monthLabel: string;
  new: number;
  returning: number;
  repeatRate: number;
}

// Format bulan "2026-10" → "Oct"
function formatMonthLabel(yyyyMm: string): string {
  const [year, month] = yyyyMm.split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleDateString("en-US", { month: "short" });
}

// Format bulan dengan year untuk tooltip "Oct 2026"
function formatMonthFull(yyyyMm: string): string {
  const [year, month] = yyyyMm.split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);
  return date.toLocaleDateString("en-US", { month: "short", year: "numeric" });
}

// Custom tooltip
interface TooltipProps {
  active?: boolean;
  payload?: Array<{
    payload: ChartDataPoint & { originalMonth: string };
  }>;
}

function CustomTooltip({ active, payload }: TooltipProps) {
  if (!active || !payload || payload.length === 0) return null;

  const data = payload[0].payload;
  const total = data.new + data.returning;

  return (
    <div
      className="p-3 rounded-lg shadow-xl border"
      style={{
        backgroundColor: "#1c130e",
        borderColor: "#2d1810",
        color: "#fef3e2",
        minWidth: "200px",
      }}
    >
      <p className="font-bold text-sm mb-2">
        {formatMonthFull(data.originalMonth)}
      </p>
      <div className="space-y-1 text-xs">
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: "#F88F22" }}
            />
            <span style={{ color: "#c9a67d" }}>New:</span>
          </div>
          <span className="font-semibold tabular-nums">
            {data.new.toLocaleString()}
          </span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: "#FBB931" }}
            />
            <span style={{ color: "#c9a67d" }}>Returning:</span>
          </div>
          <span className="font-semibold tabular-nums">
            {data.returning.toLocaleString()}
          </span>
        </div>
        <div className="pt-1 mt-1 border-t" style={{ borderColor: "#2d1810" }}>
          <div className="flex items-center justify-between gap-4">
            <span style={{ color: "#c9a67d" }}>Total Active:</span>
            <span className="font-bold tabular-nums">
              {total.toLocaleString()}
            </span>
          </div>
          <div className="flex items-center justify-between gap-4 mt-1">
            <span style={{ color: "#c9a67d" }}>Repeat Rate:</span>
            <span
              className="font-semibold tabular-nums"
              style={{ color: "#FFE3B3" }}
            >
              {data.repeatRate.toFixed(1)}%
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

function CustomerAcquisitionTrend() {
  const [data, setData] = useState<AcquisitionTrend | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get<AcquisitionTrend>(
          "http://localhost:8000/api/customers/acquisition-trend",
          {
            params: { months: 12 },
          }
        );
        setData(response.data);
      } catch (err) {
        setError("Failed to fetch acquisition trend");
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
        Loading acquisition trend...
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

  if (!data || data.data_points.length === 0) return null;

  // Transform ke chart format
  const chartData = data.data_points.map((p) => ({
    monthLabel: formatMonthLabel(p.month),
    originalMonth: p.month,
    new: p.new_customers,
    returning: p.returning_customers,
    repeatRate: Number(p.repeat_rate_percent),
  }));

  // Header context
  const momChange = data.mom_change_percent ? Number(data.mom_change_percent) : null;
  const currentRepeatRate = Number(data.current_repeat_rate);
  const currentMonthLabel = formatMonthLabel(data.end_month);

  // Trend direction
  const isPositive = momChange !== null && momChange > 0;
  const isNegative = momChange !== null && momChange < 0;
  const TrendIcon = isPositive ? TrendingUp : isNegative ? TrendingDown : Minus;
  const trendColor = isPositive
    ? "var(--color-success)"
    : isNegative
    ? "var(--color-danger)"
    : "var(--text-tertiary)";

  return (
    <div className="bg-card p-6 rounded-lg border border-subtle space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs text-tertiary uppercase tracking-wide">
            Acquisition & Retention
          </p>
          <h2 className="text-xl font-semibold text-primary mt-1">
            New vs Returning Customers
          </h2>
          <div className="mt-2 flex items-center gap-4 flex-wrap">
            <p className="text-2xl font-bold text-primary tabular-nums">
              {data.current_month_total.toLocaleString()}
              <span className="text-sm font-normal text-tertiary ml-2">
                customers in {currentMonthLabel}
              </span>
            </p>
          </div>
          {momChange !== null && (
            <div
              className="flex items-center gap-1 text-xs mt-2"
              style={{ color: trendColor }}
            >
              <TrendIcon size={14} />
              <span className="font-semibold tabular-nums">
                {isPositive && "+"}
                {momChange}%
              </span>
              <span style={{ color: "var(--text-tertiary)" }}>
                vs prev. month · repeat rate {currentRepeatRate.toFixed(1)}%
              </span>
            </div>
          )}
        </div>

        {/* Legend custom di header */}
        <div className="flex items-center gap-4 text-xs flex-wrap">
          <div className="flex items-center gap-1.5">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: "#F88F22" }}
            />
            <span className="text-secondary">New (left)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div
              className="w-3 h-3 rounded-sm"
              style={{ backgroundColor: "#FBB931" }}
            />
            <span className="text-secondary">Returning (left)</span>
          </div>
          <div className="flex items-center gap-1.5">
            <div
              className="w-5 h-0 border-t-2 border-dashed"
              style={{ borderColor: "#FFE3B3" }}
            />
            <span className="text-secondary">Repeat rate % (right)</span>
          </div>
        </div>
      </div>

      {/* Chart */}
      <div className="w-full" style={{ height: "320px" }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={chartData}
            margin={{ top: 10, right: 10, left: -10, bottom: 0 }}
          >
            {/* Gradient defs untuk area fill */}
            <defs>
              <linearGradient id="newGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#F88F22" stopOpacity={0.6} />
                <stop offset="100%" stopColor="#F88F22" stopOpacity={0.1} />
              </linearGradient>
              <linearGradient id="returningGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#FBB931" stopOpacity={0.5} />
                <stop offset="100%" stopColor="#FBB931" stopOpacity={0.1} />
              </linearGradient>
            </defs>

            <CartesianGrid
              strokeDasharray="3 3"
              stroke="#2d1810"
              vertical={false}
            />

            <XAxis
              dataKey="monthLabel"
              stroke="#8b6f52"
              tick={{ fill: "#c9a67d", fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: "#2d1810" }}
            />

            {/* LEFT Y-axis: counts */}
            <YAxis
              yAxisId="left"
              stroke="#8b6f52"
              tick={{ fill: "#c9a67d", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => {
                if (value >= 1000) return `${(value / 1000).toFixed(1)}k`;
                return value.toString();
              }}
            />

            {/* RIGHT Y-axis: percentage */}
            <YAxis
              yAxisId="right"
              orientation="right"
              stroke="#8b6f52"
              tick={{ fill: "#c9a67d", fontSize: 11 }}
              tickLine={false}
              axisLine={false}
              tickFormatter={(value) => `${value}%`}
              domain={[0, 100]}
            />

            <Tooltip content={<CustomTooltip />} />

            {/* Returning area (stacked bottom) */}
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="returning"
              stackId="1"
              stroke="#FBB931"
              strokeWidth={2}
              fill="url(#returningGradient)"
              name="Returning"
            />

            {/* New area (stacked top) */}
            <Area
              yAxisId="left"
              type="monotone"
              dataKey="new"
              stackId="1"
              stroke="#F88F22"
              strokeWidth={2}
              fill="url(#newGradient)"
              name="New"
            />

            {/* Repeat rate line (dashed, right axis) */}
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="repeatRate"
              stroke="#FFE3B3"
              strokeWidth={2}
              strokeDasharray="5 5"
              dot={{ fill: "#FFE3B3", r: 3 }}
              activeDot={{ r: 5 }}
              name="Repeat Rate"
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export default CustomerAcquisitionTrend;
