import { useState, useEffect } from "react";
import axios from "axios";

interface ChannelMetrics {
  channel: string;
  new_customers: number;
  pct_of_total: string;
  repeat_by_m3_pct: string;
  avg_projected_12mo_value: string;
  hibernating_pct: string;
}

interface AcquisitionChannelQualityResponse {
  cohort_start: string;
  cohort_end: string;
  total_new_customers: number;
  avg_repeat_by_m3_pct: string;
  top_channel: string;
  top_channel_share: string;
  top_channel_repeat_rate: string;
  channels: ChannelMetrics[];
}

// ===== Helpers =====

// Hibernating pill color by severity
// < 20% = healthy (green), 20-35% = warning (yellow), >= 35% = critical (red)
function getHibernatingColor(pct: number): {
  bg: string;
  text: string;
  dot: string;
} {
  if (pct >= 35)
    return {
      bg: "rgba(239, 68, 68, 0.12)",
      text: "#f87171",
      dot: "#ef4444",
    };
  if (pct >= 20)
    return {
      bg: "rgba(251, 185, 49, 0.12)",
      text: "#FBB931",
      dot: "#FBB931",
    };
  return {
    bg: "rgba(74, 222, 128, 0.12)",
    text: "#4ade80",
    dot: "#22c55e",
  };
}

// Format "2026-01-02" → "Jan 2, 2026"
function formatDate(dateStr: string): string {
  const [year, month, day] = dateStr.split("-");
  const date = new Date(Number(year), Number(month) - 1, Number(day));
  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

// Format cohort range: "Jan 2 – Apr 2, 2026"
function formatCohortRange(start: string, end: string): string {
  return `${formatDate(start)} – ${formatDate(end)}`;
}

// ===== Component =====

function AcquisitionChannelQuality() {
  const [data, setData] =
    useState<AcquisitionChannelQualityResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get<AcquisitionChannelQualityResponse>(
          "http://localhost:8000/api/customers/acquisition-channel-quality"
        );
        setData(response.data);
      } catch (err) {
        setError("Failed to fetch acquisition channel quality");
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
        Loading channel quality...
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

  if (!data || data.channels.length === 0) return null;

  const avgRepeatRate = Number(data.avg_repeat_by_m3_pct);
  const topShare = Number(data.top_channel_share);
  const topRepeat = Number(data.top_channel_repeat_rate);

  // Scale untuk progress bar: pakai max rate antar channel + avg,
  // dibulatkan ke atas kelipatan 10 untuk angka bersih
  const maxRepeatRate = Math.max(
    ...data.channels.map((c) => Number(c.repeat_by_m3_pct)),
    avgRepeatRate
  );
  const barScale = Math.max(Math.ceil(maxRepeatRate / 10) * 10, 10);

  // Headline conditional: "but only" kalau top channel di bawah avg,
  // "with" kalau top channel di atas avg
  const topIsBelowAvg = topRepeat < avgRepeatRate;

  return (
    <div className="bg-card p-6 rounded-lg border border-subtle space-y-4">
      {/* Header */}
      <div>
        <p className="text-xs text-tertiary uppercase tracking-wide">
          Acquisition Channel Quality
        </p>
        <h2 className="text-lg font-semibold mt-2 leading-relaxed">
          <span className="text-primary text-xl">{topShare.toFixed(0)}%</span>
          <span className="text-secondary font-normal">
            {" "}
            dari new customers datang dari{" "}
          </span>
          <span className="text-primary">{data.top_channel}</span>
          <span className="text-secondary font-normal">
            {topIsBelowAvg ? ", tapi hanya " : ", dengan "}
          </span>
          <span
            style={{
              color: topIsBelowAvg ? "#f87171" : "#4ade80",
            }}
            className="text-xl"
          >
            {topRepeat.toFixed(1)}%
          </span>
          <span className="text-secondary font-normal">
            {" "}
            return by M3
          </span>
        </h2>
        <p className="text-xs text-tertiary mt-2 leading-relaxed">
          Channel of each customer's first order (Shopify attribution) · cohort{" "}
          <span className="text-secondary">
            {formatCohortRange(data.cohort_start, data.cohort_end)}
          </span>{" "}
          ({data.total_new_customers.toLocaleString()} customers) · average
          repeat by M3:{" "}
          <span style={{ color: "#FFE3B3" }} className="font-semibold">
            {avgRepeatRate.toFixed(1)}%
          </span>
        </p>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr style={{ borderBottom: "1px solid #2d1810" }}>
              <th className="text-left text-xs font-medium text-tertiary uppercase tracking-wide py-3">
                First-Order Channel
              </th>
              <th className="text-right text-xs font-medium text-tertiary uppercase tracking-wide py-3 whitespace-nowrap px-4">
                New Customers
              </th>
              <th
                className="text-left text-xs font-medium text-tertiary uppercase tracking-wide py-3 whitespace-nowrap px-4"
                style={{ minWidth: "260px" }}
              >
                Repeat by M3
              </th>
              <th className="text-right text-xs font-medium text-tertiary uppercase tracking-wide py-3 whitespace-nowrap px-4">
                Avg 12-mo Value
              </th>
              <th className="text-right text-xs font-medium text-tertiary uppercase tracking-wide py-3 whitespace-nowrap px-4">
                Now Hibernating
              </th>
            </tr>
          </thead>
          <tbody>
            {data.channels.map((channel, idx) => {
              const repeat = Number(channel.repeat_by_m3_pct);
              const hibernating = Number(channel.hibernating_pct);
              const value = Number(channel.avg_projected_12mo_value);
              const share = Number(channel.pct_of_total);
              const isUnknown = channel.channel === "Unknown";
              const isLastRow = idx === data.channels.length - 1;

              const hibernateColor = getHibernatingColor(hibernating);
              const barWidth = Math.min((repeat / barScale) * 100, 100);
              const tickPosition = Math.min(
                (avgRepeatRate / barScale) * 100,
                100
              );

              // Highlight: above average = bright orange, below = muted
              const repeatIsAboveAvg = repeat >= avgRepeatRate;

              return (
                <tr
                  key={channel.channel}
                  style={{
                    borderBottom: isLastRow ? "none" : "1px solid #1f140d",
                  }}
                  className="hover:bg-black/10 transition-colors"
                >
                  <td
                    className="py-3.5 text-sm"
                    style={{
                      color: isUnknown ? "#8b6f52" : undefined,
                    }}
                  >
                    <span className={isUnknown ? "" : "text-primary"}>
                      {channel.channel}
                    </span>
                  </td>
                  <td className="py-3.5 text-right text-sm tabular-nums px-4 whitespace-nowrap">
                    <span className="text-secondary">
                      {channel.new_customers.toLocaleString()}
                    </span>
                    <span className="text-tertiary"> · {share.toFixed(0)}%</span>
                  </td>
                  <td className="py-3.5 px-4">
                    {isUnknown ? (
                      <div className="flex items-center gap-3">
                        <div
                          className="relative flex-1 h-2 rounded-full"
                          style={{ backgroundColor: "#2d1810" }}
                        />
                        <span
                          className="text-sm text-tertiary tabular-nums whitespace-nowrap"
                          style={{ minWidth: "48px" }}
                        >
                          —
                        </span>
                      </div>
                    ) : (
                      <div className="flex items-center gap-3">
                        {/* Progress bar track */}
                        <div
                          className="relative flex-1 h-2 rounded-full overflow-visible"
                          style={{ backgroundColor: "#2d1810" }}
                        >
                          {/* Filled portion */}
                          <div
                            className="absolute left-0 top-0 h-full rounded-full"
                            style={{
                              width: `${barWidth}%`,
                              backgroundColor: "#F88F22",
                              transition: "width 0.3s ease",
                            }}
                          />
                          {/* Average benchmark tick (vertical line) */}
                          <div
                            className="absolute top-1/2 -translate-y-1/2 rounded-sm"
                            style={{
                              left: `${tickPosition}%`,
                              width: "2px",
                              height: "14px",
                              backgroundColor: "#FFE3B3",
                              transform: "translate(-50%, -50%)",
                            }}
                          />
                        </div>
                        <span
                          className="text-sm font-semibold tabular-nums whitespace-nowrap"
                          style={{
                            minWidth: "48px",
                            color: repeatIsAboveAvg ? "#F88F22" : "#c9a67d",
                          }}
                        >
                          {repeat.toFixed(1)}%
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="py-3.5 text-right text-sm tabular-nums px-4 whitespace-nowrap">
                    {isUnknown ? (
                      <span className="text-tertiary">—</span>
                    ) : (
                      <span className="text-secondary">
                        ${value.toLocaleString()}
                      </span>
                    )}
                  </td>
                  <td className="py-3.5 text-right px-4 whitespace-nowrap">
                    {isUnknown ? (
                      <span
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs"
                        style={{
                          backgroundColor: "rgba(139, 111, 82, 0.12)",
                          color: "#8b6f52",
                        }}
                      >
                        <span
                          className="w-1.5 h-1.5 rounded-full"
                          style={{ backgroundColor: "#8b6f52" }}
                        />
                        —
                      </span>
                    ) : (
                      <span
                        className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold tabular-nums"
                        style={{
                          backgroundColor: hibernateColor.bg,
                          color: hibernateColor.text,
                        }}
                      >
                        <span
                          className="w-1.5 h-1.5 rounded-full"
                          style={{ backgroundColor: hibernateColor.dot }}
                        />
                        {hibernating.toFixed(0)}%
                      </span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Footer */}
      <div
        className="text-xs text-tertiary pt-3 flex items-center gap-3 flex-wrap"
        style={{ borderTop: "1px solid #1f140d" }}
      >
        <span className="flex items-center gap-1.5">
          <span
            className="inline-block rounded-sm"
            style={{
              width: "2px",
              height: "10px",
              backgroundColor: "#FFE3B3",
            }}
          />
          Tick on each bar = average ({avgRepeatRate.toFixed(1)}%)
        </span>
        <span>·</span>
        <span>
          <span style={{ color: "#8b6f52" }}>Unknown</span> = first order before
          attribution sync or journey not ready yet
        </span>
      </div>
    </div>
  );
}

export default AcquisitionChannelQuality;
