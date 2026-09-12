import { LayoutDashboard } from "lucide-react";
import Header from "./Header";

interface NavItem {
    label: string;
    icon: React.ReactNode;
    active?: boolean;
}

const navItems: NavItem[] = [
    { label: "Overview", icon: <LayoutDashboard size={16} />, active: true },
];

function Sidebar() {
    return (
        <div className="flex-none w-56 h-full flex flex-col bg-white border-r border-gray-200">
            {/* Brand */}
            <div className="flex-none px-3 py-2 border-b border-gray-200">
                <Header title="Business Dashboard" subtitle="Real-time revenue metrics" />
            </div>

            {/* Nav items */}
            <nav className="flex-1 min-h-0 overflow-y-auto p-2 space-y-1">
                {navItems.map((item) => (
                    <div
                        key={item.label}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium cursor-pointer transition-colors ${
                            item.active
                                ? "bg-blue-50 text-blue-600"
                                : "text-gray-600 hover:bg-gray-50"
                        }`}
                    >
                        {item.icon}
                        {item.label}
                    </div>
                ))}
            </nav>
        </div>
    );
}

export default Sidebar;
