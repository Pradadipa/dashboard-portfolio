import { Users } from "lucide-react";

// Placeholder: belum ada endpoint customer di backend.
function CustomersPage() {
    return (
        <div className="h-full min-h-80 rounded-lg bg-card border border-subtle flex flex-col items-center justify-center gap-2 text-center p-6">
            <Users size={32} className="text-tertiary" />
            <h2 className="text-base font-semibold text-primary">Customers</h2>
            <p className="text-sm text-tertiary">Customer metrics are coming soon.</p>
        </div>
    );
}

export default CustomersPage;
