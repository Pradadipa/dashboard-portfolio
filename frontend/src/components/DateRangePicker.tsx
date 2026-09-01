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
        <div>
            <label>
                Start Date:{" "}
                <input 
                    type="date"
                    value={startDate} // value from props
                    onChange={(e) => onStartDateChange(e.target.value)} // Callbacck if any change 
                /> 
            </label>
            {"  "}
            <label>
                End Date: {" "}
                <input 
                    type="date"
                    value={endDate}
                    onChange={(e) => onEndDateChange(e.target.value)}
                />
            </label>
        </div>
    );
}

export default DateRangePicker;