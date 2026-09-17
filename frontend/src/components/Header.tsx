interface HeaderProps {
    title: string;
    subtitle?: string;
}

function Header({ title, subtitle } : HeaderProps) {
    return (
        <div>
            <h1 className="text-xs font-medium text-secondary">{title}</h1>
            {subtitle && <p className="text-lg  text-primary">{subtitle}</p>}
        </div>
    );
}

export default Header;