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
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
            {items.map((item) => (
                <KpiCard
                    key={item.label}
                    label={item.label}
                    value={item.value}
                />
            ))}
        </div>
    );
}

export default KpiList;