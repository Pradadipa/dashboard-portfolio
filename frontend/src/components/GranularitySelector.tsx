// Type for granularity options
type Granularity = "day" | "week" | "month";

interface GranularitySelectorProps {
    value: Granularity;
    onChange: (value: Granularity) => void;
}

function GranularitySelector({ value, onChange } : GranularitySelectorProps ) {
    return (
        <div>
            <label>
                Granularity:{" "}
                <select
                    value={value}
                    onChange={(e) => onChange(e.target.value as Granularity)}
                >
                    <option value="day">DAY</option>
                    <option value="week">WEEK</option>
                    <option value="month">MONTH</option>
                </select>
            </label>
        </div>
    );
}

export default GranularitySelector;

export type { Granularity };