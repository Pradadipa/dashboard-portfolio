// Type for granularity options
type Granularity = "day" | "week" | "month";

interface GranularitySelectorProps {
    value: Granularity;
    onChange: (value: Granularity) => void;
}

function GranularitySelector({ value, onChange } : GranularitySelectorProps ) {
    return (
        <div className="flex items-center gap-2">
            <label className="text-sm font-medium text-gray-700">
                Granularity: 
            </label>
            <select
                value={value}
                onChange={(e) => onChange(e.target.value as Granularity)}
                className="border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
                <option value="day">DAY</option>
                <option value="week">WEEK</option>
                <option value="month">MONTH</option>
            </select>
        </div>
    );
}

export default GranularitySelector;

export type { Granularity };