interface HeaderProps {
    title: string;
    subtitle?: string;
}

function Header({ title, subtitle } : HeaderProps) {
    return (
        <div>
            <h1 className="text-3x1 font-bold text-gray-900">{title}</h1>
            {subtitle && <p className="text-gray-600 mt-1">{subtitle}</p>}
        </div>
    );
}

export default Header;