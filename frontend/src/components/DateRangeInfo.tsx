interface DateRangeInfoProps {
    startDate: string;
    endDate: string;
}

function DateRangeInfo({ startDate, endDate} : DateRangeInfoProps) {
    return (
        <p>Period: {startDate} to {endDate}</p>
    );
}

export default DateRangeInfo;