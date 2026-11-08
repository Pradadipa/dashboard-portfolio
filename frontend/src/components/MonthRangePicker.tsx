import { Calendar } from "lucide-react";
import { formatMonth, listMonths } from "../lib/monthRange";

interface MonthRangePickerProps {
    startMonth: string;
    endMonth: string;
    firstMonth: string;
    lastMonth: string;
    onChange: (startMonth: string, endMonth: string) => void;
}

const SELECT_CLASS =
    "min-w-0 flex-1 sm:flex-none bg-card text-xs text-primary focus:outline-none [color-scheme:dark]";

function MonthRangePicker({
    startMonth,
    endMonth,
    firstMonth,
    lastMonth,
    onChange,
}: MonthRangePickerProps) {
    const months = listMonths(firstMonth, lastMonth);

    const options = months.map((month) => (
        // Warna eksplisit: browser tidak selalu mewarisi warna select ke daftar option
        <option key={month} value={month} className="bg-card text-primary">
            {formatMonth(month)}
        </option>
    ));

    return (
        <div className="w-full sm:w-auto inline-flex items-center gap-2 bg-card border border-subtle rounded-lg px-3 py-1.5">
            <Calendar size={14} className="text-tertiary flex-shrink-0" />

            <select
                aria-label="Start month"
                value={startMonth}
                // Bulan akhir ikut maju supaya range tidak pernah terbalik
                onChange={(e) =>
                    onChange(e.target.value, e.target.value > endMonth ? e.target.value : endMonth)
                }
                className={SELECT_CLASS}
            >
                {options}
            </select>

            <span className="text-tertiary text-xs">-</span>

            <select
                aria-label="End month"
                value={endMonth}
                // Bulan mulai ikut mundur supaya range tidak pernah terbalik
                onChange={(e) =>
                    onChange(e.target.value < startMonth ? e.target.value : startMonth, e.target.value)
                }
                className={SELECT_CLASS}
            >
                {options}
            </select>
        </div>
    );
}

export default MonthRangePicker;
