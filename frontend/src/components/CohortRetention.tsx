import { useState, useEffect } from "react";
import axios from "axios";

interface CohortRetentionCell {
  period_number: number;
  returners: number;
  retention_pct: number | null;
}

interface CohortRetentionRow {
  cohort_month: string; // ISO date "2025-11-01"
  cohort_size: number;
  cells: CohortRetentionCell[];
}

interface CohortRetentionResponse {
  cohort_count: number;
  period_count: number;
  rows: CohortRetentionRow[];
}

// Format "2025-11-01" → "Nov '25"
function formatCohortMonth(dateStr: string): string {
  const [year, month] = dateStr.split("-");
  const date = new Date(Number(year), Number(month) - 1, 1);
  const monthShort = date.toLocaleDateString("en-US", { month: "short" });
  const yearShort = year.slice(2);
  return `${monthShort} '${yearShort}`;
}

// Map retention % → background color.
// Scale: 0% → 10% maps to opacity 0.08 → 0.95
function getRetentionBg(pct: number | null): string {
  if (pct === null) return "transparent";
  const normalized = Math.min(Math.max(pct / 10, 0), 1);
  const opacity = 0.08 + normalized * 0.87;
  return `rgba(248, 143, 34, ${opacity.toFixed(3)})`;
}

// Text color — switch to dark text when cell bg terlalu terang
function getRetentionTextColor(pct: number | null): string {
  if (pct === null) return "#8b6f52";
  if (pct >= 6) return "#1c130e"; // dark text on bright orange
  return "#fef3e2"; // light text on dark orange
}

function CohortRetention() {
  const [data, setData] = useState<CohortRetentionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      try {
        const response = await axios.get<CohortRetentionResponse>(
          "http://localhost:8000/api/customers/cohort-retention",
          {
            params: { cohort_count: 12, period_count: 6 },
          }
        );
        setData(response.data);
      } catch (err) {
        setError("Failed to fetch cohort retention");
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
        Loading cohort retention...
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

  if (!data || data.rows.length === 0) return null;

  const periodNumbers = Array.from(
    { length: data.period_count },
    (_, i) => i + 1
  );

  // Weighted average per period (bobot = cohort_size)
  // Alasan: cohort kecil tidak boleh menyeret rata-rata secara disproporsional
  const avgPerPeriod = periodNumbers.map((period) => {
    let weightedSum = 0;
    let totalWeight = 0;
    for (const row of data.rows) {
      const cell = row.cells.find((c) => c.period_number === period);
      if (cell && cell.retention_pct !== null) {
        weightedSum += cell.retention_pct * row.cohort_size;
        totalWeight += row.cohort_size;
      }
    }
    return totalWeight > 0 ? weightedSum / totalWeight : null;
  });

  // Best cohort indicator — cohort dengan M+1 tertinggi
  const bestCohortM1 = data.rows.reduce<{ month: string; pct: number } | null>(
    (best, row) => {
      const m1 = row.cells.find((c) => c.period_number === 1)?.retention_pct;
      if (m1 === null || m1 === undefined) return best;
      if (!best || m1 > best.pct) {
        return { month: row.cohort_month, pct: m1 };
      }
      return best;
    },
    null
  );

  return (
    <div className="bg-card p-6 rounded-lg border border-subtle space-y-4">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 flex-wrap">
        <div>
          <p className="text-xs text-tertiary uppercase tracking-wide">
            Retention Analysis
          </p>
          <h2 className="text-xl font-semibold text-primary mt-1">
            Cohort Retention Matrix
          </h2>
          <p className="text-sm text-secondary mt-1 max-w-xl">
            % customer dari tiap cohort yang kembali belanja di bulan-bulan
            berikutnya. Baca horizontal untuk lihat decay satu cohort, vertikal
            untuk bandingkan cohort.
          </p>
          {bestCohortM1 && (
            <p
              className="text-xs mt-2 tabular-nums"
              style={{ color: "#FFE3B3" }}
            >
              <span className="font-semibold">Best M+1:</span>{" "}
              {formatCohortMonth(bestCohortM1.month)} ·{" "}
              {bestCohortM1.pct.toFixed(2)}%
            </p>
          )}
        </div>

        {/* Color scale legend */}
        <div className="flex items-center gap-2 text-xs">
          <span className="text-tertiary tabular-nums">0%</span>
          <div className="flex rounded overflow-hidden border border-subtle">
            {[0.08, 0.25, 0.45, 0.65, 0.85, 0.95].map((op) => (
              <div
                key={op}
                className="w-6 h-4"
                style={{ backgroundColor: `rgba(248, 143, 34, ${op})` }}
              />
            ))}
          </div>
          <span className="text-tertiary tabular-nums">10%+</span>
        </div>
      </div>

      {/* Heatmap Table */}
      <div className="overflow-x-auto">
        <table
          className="w-full"
          style={{ borderCollapse: "separate", borderSpacing: "3px 3px" }}
        >
          <thead>
            <tr>
              <th className="text-left text-xs font-medium text-tertiary uppercase tracking-wide px-2 py-2 whitespace-nowrap">
                Cohort
              </th>
              <th className="text-right text-xs font-medium text-tertiary uppercase tracking-wide px-2 py-2 whitespace-nowrap">
                Size
              </th>
              {periodNumbers.map((period) => (
                <th
                  key={period}
                  className="text-center text-xs font-medium text-tertiary uppercase tracking-wide px-2 py-2"
                  style={{ minWidth: "68px" }}
                >
                  M+{period}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {data.rows.map((row) => (
              <tr key={row.cohort_month}>
                <td className="text-sm font-medium text-primary px-2 py-1 whitespace-nowrap">
                  {formatCohortMonth(row.cohort_month)}
                </td>
                <td className="text-sm text-secondary text-right tabular-nums px-2 py-1 whitespace-nowrap">
                  {row.cohort_size.toLocaleString()}
                </td>
                {periodNumbers.map((period) => {
                  const cell = row.cells.find(
                    (c) => c.period_number === period
                  );
                  const pct = cell?.retention_pct ?? null;
                  const isIncomplete = pct === null;

                  return (
                    <td
                      key={period}
                      className="text-center text-xs font-semibold tabular-nums rounded"
                      style={{
                        backgroundColor: getRetentionBg(pct),
                        color: getRetentionTextColor(pct),
                        padding: "10px 8px",
                        border: isIncomplete
                          ? "1px dashed #2d1810"
                          : "1px solid transparent",
                        transition: "transform 0.15s ease",
                      }}
                      title={
                        cell
                          ? isIncomplete
                            ? "Period belum lengkap"
                            : `${cell.returners.toLocaleString()} customers · ${pct!.toFixed(2)}%`
                          : ""
                      }
                    >
                      {isIncomplete ? "–" : `${pct!.toFixed(1)}%`}
                    </td>
                  );
                })}
              </tr>
            ))}

            {/* Average row (weighted) */}
            <tr>
              <td
                className="text-sm font-bold text-primary px-2 pt-4 pb-1 whitespace-nowrap"
                style={{ borderTop: "2px solid #2d1810" }}
              >
                Avg (weighted)
              </td>
              <td style={{ borderTop: "2px solid #2d1810" }}></td>
              {avgPerPeriod.map((avg, i) => (
                <td
                  key={i}
                  className="text-center text-xs font-bold tabular-nums px-2 pt-4 pb-1"
                  style={{
                    color: "#FFE3B3",
                    borderTop: "2px solid #2d1810",
                  }}
                >
                  {avg !== null ? `${avg.toFixed(1)}%` : "–"}
                </td>
              ))}
            </tr>
          </tbody>
        </table>
      </div>

      {/* Footer legend */}
      <div className="text-xs text-tertiary pt-2 border-t border-subtle space-x-3">
        <span>
          <span className="font-semibold text-secondary">M+N</span> = N bulan
          setelah first purchase
        </span>
        <span>·</span>
        <span>
          <span
            className="inline-block w-2 h-2 mr-1 align-middle rounded"
            style={{ border: "1px dashed #8b6f52" }}
          />
          period belum lengkap
        </span>
        <span>·</span>
        <span>Hover cell untuk detail jumlah returners</span>
      </div>
    </div>
  );
}

export default CohortRetention;
