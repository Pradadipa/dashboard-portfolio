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
        <div className="bg-white rounded-lg shadow flex gap-3 items-end">
            <div className="flex flex-col">
                <label className="text-xs font-medium text-gray-700 mb-0.5">
                    Start Date
                </label>
                <input
                    type="date"
                    value={startDate} // value from props
                    onChange={(e) => onStartDateChange(e.target.value)} // Callbacck if any change
                    className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
            </div>

            <div className="flex flex-col">
                <label className="text-xs font-medium text-gray-700 mb-0.5">
                    End Date
                </label>
                <input
                    type="date"
                    value={endDate}
                    onChange={(e) => onEndDateChange(e.target.value)}
                    className="border border-gray-300 rounded px-2 py-1 text-xs focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
            </div>
        </div>
    );
}

export default DateRangePicker;