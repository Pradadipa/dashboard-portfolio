import { Calendar } from "lucide-react";

interface DateRangePickerProps {
    startDate: string;
    endDate: string;
    onStartDateChange: (value: string) => void;
    onEndDateChange: (value: string) => void;
}

function DateRangePicker({
    startDate,
    endDate,
    onStartDateChange,
    onEndDateChange,
}: DateRangePickerProps) {
    return (
        <div className="flex items-center gap-2 bg-card border border-subtle rounded-lg px-3 py-1.5">
            <Calendar size={14} className="text-tertiary flex-shrink-0" />

            <input
                type="date"
                aria-label="Start date"
                value={startDate} // value from props
                onChange={(e) => onStartDateChange(e.target.value)} // Callbacck if any change
                className="bg-transparent text-xs text-primary focus:outline-none [color-scheme:dark]"
            />

            <span className="text-tertiary text-xs">-</span>

            <input
                type="date"
                aria-label="End date"
                value={endDate}
                onChange={(e) => onEndDateChange(e.target.value)}
                className="bg-transparent text-xs text-primary focus:outline-none [color-scheme:dark]"
            />
        </div>
    );
}

export default DateRangePicker;