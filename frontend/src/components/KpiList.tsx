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
    iconColor?: string;
    sparklineColor?: string;
}

interface KpiListProps {
    items: KpiItem[];
}

function KpiList ({ items } : KpiListProps) {
    return (
        <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-5 gap-2 sm:gap-3 [&>*:last-child:nth-child(odd)]:col-span-2 md:[&>*:last-child:nth-child(odd)]:col-span-1">
            {items.map((item) => (
                <KpiCard
                    key={item.label}
                    label={item.label}
                    value={item.value}
                    changePercent={item.changePercent}
                    icon={item.icon}
                    iconColor={item.iconColor}
                    sparklineData={item.sparklineData}
                    sparklineColor={item.sparklineColor}
                />
            ))}
        </div>
    );
}

export default KpiList;