interface HeaderProps {
    title: string;
    subtitle?: string;
}

function Header({ title, subtitle } : HeaderProps) {
    return (
        <div>
            <h1>{title}</h1>
            {subtitle && <p>{subtitle}</p>}
        </div>
    );
}

export default Header;