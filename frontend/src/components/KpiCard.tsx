interface KpiCardProps {
    label: string;
    value: string;
}

function KpiCard({ label, value} : KpiCardProps) {
    return (
        <div className="bg-white p-6 rounded-lg shadow hover:shadow-lg transition-shadow">
            <p className="text-sm font-medium text-gray-600 uppercase tracking-wide">
                {label}
            </p>
            <p className="text-3xl font-bold text-gray-900 mt-2">
                {value}
            </p>
        </div>
    );
}

export default KpiCard;