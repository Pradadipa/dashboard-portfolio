interface KpiCardProps {
    label: string;
    value: string;
}

function KpiCard({ label, value} : KpiCardProps) {
    return (
        <li>
            <strong>{label}:</strong> {value}
        </li>
    );
}

export default KpiCard;