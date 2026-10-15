import { NavLink } from "react-router-dom";
import { LayoutDashboard, Users, X } from "lucide-react";

interface NavItem {
  path: string;
  label: string;
  icon: React.ReactNode;
  end?: boolean;  // untuk match exact (buat root path "/")
}

const navItems: NavItem[] = [
  { path: "/", label: "Overview", icon: <LayoutDashboard size={16} />, end: true },
  { path: "/customers", label: "Customers", icon: <Users size={16} /> },
];

interface SidebarProps {
  open: boolean;
  onClose: () => void;
  onNavigate: () => void;
}

function Sidebar({ open, onClose, onNavigate }: SidebarProps) {
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

        {/* Nav items — pakai NavLink untuk auto active state */}
        <nav className="flex-1 min-h-0 overflow-y-auto p-2 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              onClick={onNavigate}
              className={({ isActive }) =>
                `w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-left transition-colors ${
                  isActive
                    ? "bg-card-hover text-[var(--accent-primary)]"
                    : "text-secondary hover:bg-card-hover hover:text-primary"
                }`
              }
            >
              {item.icon}
              {item.label}
            </NavLink>
          ))}
        </nav>
      </aside>
    </>
  );
}

export default Sidebar;
