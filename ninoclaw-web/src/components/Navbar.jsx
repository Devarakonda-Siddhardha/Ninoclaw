import { Link, useLocation } from 'react-router-dom';
import { Bot, FileText, ChevronRight } from 'lucide-react';
import './Navbar.css';

export default function Navbar() {
    const location = useLocation();

    return (
        <nav className="navbar-wrapper">
            <div className="container navbar">
                <Link to="/" className="brand">
                    <Bot className="brand-icon" size={32} />
                    <span className="brand-text">Ninoclaw</span>
                </Link>

                <div className="nav-links">
                    <Link
                        to="/"
                        className={`nav-link ${location.pathname === '/' ? 'active' : ''}`}
                    >
                        Home
                    </Link>
                    <Link
                        to="/docs"
                        className={`nav-link ${location.pathname.startsWith('/docs') ? 'active' : ''}`}
                    >
                        <FileText size={18} />
                        Documentation
                    </Link>
                    <a
                        href="https://github.com/Devarakonda-Siddhardha/Ninoclaw"
                        target="_blank"
                        rel="noreferrer"
                        className="action-btn"
                    >
                        GitHub
                        <ChevronRight size={18} />
                    </a>
                </div>
            </div>
        </nav>
    );
}
