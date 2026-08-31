import KpiCard from "./KpiCard";

interface KpiItem {
    label: string;
    value: string;
}

interface KpiListProps {
    items: KpiItem[];
}

function KpiList ({ items } : KpiListProps) {
    return (
        <ul>
            {items.map((item) => (
                <KpiCard
                    key={item.label}
                    label={item.label}
                    value={item.value}
                />
            ))}
        </ul>
    );
}

export default KpiList;