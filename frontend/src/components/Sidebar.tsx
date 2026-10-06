import { LayoutDashboard, Users, X } from "lucide-react";

export type Page = "overview" | "customers";

interface NavItem {
    page: Page;
    label: string;
    icon: React.ReactNode;
}

const navItems: NavItem[] = [
    { page: "overview", label: "Overview", icon: <LayoutDashboard size={16} /> },
    { page: "customers", label: "Customers", icon: <Users size={16} /> },
];

interface SidebarProps {
    open: boolean;
    onClose: () => void;
    activePage: Page;
    onNavigate: (page: Page) => void;
}

// desk (layar besar): sidebar statis di kiri, menggeser konten.
// Di bawah desk: drawer di atas konten + backdrop; klik backdrop/✕ untuk menutup.
function Sidebar({ open, onClose, activePage, onNavigate }: SidebarProps) {
    return (
        <>
            {open && (
                <div
                    className="fixed inset-0 z-30 bg-black/60 desk:hidden"
                    onClick={onClose}
                    aria-hidden="true"
                />
            )}

            <aside
                className={`${open ? "flex" : "hidden"} fixed inset-y-0 left-0 z-40 w-64 shadow-xl desk:static desk:z-auto desk:w-56 desk:shadow-none flex-none h-full flex-col bg-card border-r border-subtle`}
            >
                {/* Brand */}
                <div className="flex-none flex items-start justify-between gap-2 px-3 py-3 border-b border-subtle">
                    <div>
                        <h1 className="text-base font-bold text-primary">Business Dashboard</h1>
                        <p className="text-xs text-tertiary mt-0.5">Real-time revenue metrics</p>
                    </div>
                    <button
                        type="button"
                        onClick={onClose}
                        aria-label="Close sidebar"
                        className="p-1 rounded-md text-tertiary hover:text-primary hover:bg-card-hover transition-colors"
                    >
                        <X size={16} />
                    </button>
                </div>

                {/* Nav items */}
                <nav className="flex-1 min-h-0 overflow-y-auto p-2 space-y-1">
                    {navItems.map((item) => {
                        const active = item.page === activePage;
                        return (
                            <button
                                key={item.page}
                                type="button"
                                onClick={() => onNavigate(item.page)}
                                aria-current={active ? "page" : undefined}
                                className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-left transition-colors ${
                                    active
                                        ? "bg-card-hover text-[var(--accent-primary)]"
                                        : "text-secondary hover:bg-card-hover hover:text-primary"
                                }`}
                            >
                                {item.icon}
                                {item.label}
                            </button>
                        );
                    })}
                </nav>
            </aside>
        </>
    );
}

export default Sidebar;
