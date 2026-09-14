interface HeaderProps {
    title: string;
    subtitle?: string;
}

function Header({ title, subtitle } : HeaderProps) {
    return (
        <div>
            <h1 className="text-lg font-bold text-gray-900">{title}</h1>
            {subtitle && <p className="text-xs text-gray-600">{subtitle}</p>}
        </div>
    );
}

export default Header;