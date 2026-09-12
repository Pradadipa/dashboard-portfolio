import KpiCard from "./KpiCard";
import type { ReactNode } from "react";

interface SparklineData {
    value: number;
}

interface KpiItem {
    label: string;
    value: string;
    changePercent?: number | null;
    icon?: ReactNode;
    sparklineData?: SparklineData[];
    sparklineColor?: string;
}

interface KpiListProps {
    items: KpiItem[];
}

function KpiList ({ items } : KpiListProps) {
    return (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5 gap-3">
            {items.map((item) => (
                <KpiCard
                    key={item.label}
                    label={item.label}
                    value={item.value}
                    changePercent={item.changePercent}
                    icon={item.icon}
                    sparklineData={item.sparklineData}
                    sparklineColor={item.sparklineColor}
                />
            ))}
        </div>
    );
}

export default KpiList;