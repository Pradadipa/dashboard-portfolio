import { LayoutDashboard } from "lucide-react";

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
        <div className="flex-none w-56 h-full flex flex-col bg-card border-r border-subtle">
            {/* Brand */}
            <div className="flex-none px-3 py-3 border-b border-subtle">
                <h1 className="text-base font-bold text-primary">Business Dashboard</h1>
                <p className="text-xs text-tertiary mt-0.5">Real-time revenue metrics</p>
            </div>

            {/* Nav items */}
            <nav className="flex-1 min-h-0 overflow-y-auto p-2 space-y-1">
                {navItems.map((item) => (
                    <div
                        key={item.label}
                        className={`flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium cursor-pointer transition-colors ${
                            item.active
                                ? "bg-card-hover text-[var(--accent-primary)]"
                                : "text-secondary hover:bg-card-hover hover:text-primary"
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
