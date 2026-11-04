// Helpers untuk bulan berformat "YYYY-MM"

// "2026-07" → "2026-07-01"
export function firstDayOfMonth(yyyyMm: string): string {
  return `${yyyyMm}-01`;
}

// "2024-02" → "2024-02-29"
export function lastDayOfMonth(yyyyMm: string): string {
  const [year, month] = yyyyMm.split("-").map(Number);
  const lastDay = new Date(Date.UTC(year, month, 0)).getUTCDate();
  return `${yyyyMm}-${String(lastDay).padStart(2, "0")}`;
}

// Semua bulan dari first sampai last, terbaru lebih dulu
export function listMonths(first: string, last: string): string[] {
  const [firstYear, firstMonth] = first.split("-").map(Number);
  const [lastYear, lastMonth] = last.split("-").map(Number);
  const count = (lastYear - firstYear) * 12 + (lastMonth - firstMonth) + 1;

  return Array.from({ length: count }, (_, i) => {
    const date = new Date(Date.UTC(lastYear, lastMonth - 1 - i, 1));
    const month = String(date.getUTCMonth() + 1).padStart(2, "0");
    return `${date.getUTCFullYear()}-${month}`;
  });
}

// "2026-07" → "Jul 2026"
export function formatMonth(yyyyMm: string): string {
  const [year, month] = yyyyMm.split("-").map(Number);
  return new Date(Date.UTC(year, month - 1, 1)).toLocaleDateString("en-US", {
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
}
