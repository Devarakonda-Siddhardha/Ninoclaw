import { Link } from 'react-router-dom';
import { Bot, Code, Smartphone, Zap, Server, BrainCircuit, Activity } from 'lucide-react';
import mascotImg from '../assets/mascot.png';
import omnichannelImg from '../assets/omnichannel.png';
import './Home.css';

export default function Home() {
    return (
        <div className="home-container">
            {/* Background glow effects */}
            <div className="glow glow-purple"></div>
            <div className="glow glow-cyan"></div>

            {/* Hero Section */}
            <section className="hero">
                <div className="hero-content animate-fade-in">
                    <div className="badge">
                        <span className="pulse-dot"></span>
                        v3.0 Live - Smarter & Faster
                    </div>

                    <h1 className="hero-title">
                        Meet <span className="gradient-text">Ninoclaw</span>
                    </h1>
                    <p className="hero-subtitle">
                        The Omnichannel AI Assistant with total hardware adaptability.
                        From Telegram chatbots to full-stack React and Expo React Native mobile apps.
                    </p>

                    <div className="hero-actions">
                        <Link to="/docs" className="btn btn-primary">
                            Read the Docs <Zap size={18} fill="currentColor" />
                        </Link>
                        <a href="https://github.com/Devarakonda-Siddhardha/Ninoclaw" className="btn btn-secondary">
                            View Source <Code size={18} />
                        </a>
                    </div>
                </div>

                {/* Mascot Image */}
                <div className="hero-visual animate-float">
                    <div className="mascot-container">
                        {/* Using the generated artifact mascot image */}
                        <img src={mascotImg} alt="Bananacrab Mascot" className="mascot-img" />
                        <div className="mascot-glow"></div>
                    </div>
                </div>
            </section>

            {/* Core Architecture Features */}
            <section className="features-section">
                <h2 className="section-title">Omnichannel Architecture</h2>
                <div className="split-layout">
                    <div className="split-visual">
                        <img src={omnichannelImg} alt="Omnichannel Interface" className="feature-img" />
                    </div>
                    <div className="features-grid vertical-grid">
                        <div className="glass-panel feature-card">
                            <Smartphone className="feature-icon" size={32} />
                            <h3>Telegram & Web Chat</h3>
                            <p>Engage with Ninoclaw via Telegram, a local Flask dashboard, or a dedicated Web UI. All powered by the same runtime engine.</p>
                        </div>
                        <div className="glass-panel feature-card">
                            <BrainCircuit className="feature-icon" size={32} />
                            <h3>Smart AI Routing</h3>
                            <p>Intelligent fallback chains route basic requests to fast models (Gemini Flash) and complex tool-calls to reasoning models, with local Ollama support.</p>
                        </div>
                        <div className="glass-panel feature-card">
                            <Server className="feature-icon" size={32} />
                            <h3>Memory & Autonomy</h3>
                            <p>SQLite-backed persistent memory, cron-scheduled tasks, and background job execution keep Ninoclaw working 24/7.</p>
                        </div>
                    </div>
                </div>
            </section>

            {/* 29+ Skills Grid */}
            <section className="skills-section">
                <h2 className="section-title">29+ Autonomous Skills</h2>
                <p className="section-description">Ninoclaw is equipped with a massive library of plugins allowing it to control APIs, write code, and act on your behalf.</p>

                <div className="skills-grid">
                    {[
                        { title: 'Expo App Builder', desc: 'Scaffolds, edits, and runs React Native mobile apps.' },
                        { title: 'React Web Builder', desc: 'Generates complete React frontends dynamically.' },
                        { title: 'LinkedIn Integration', desc: 'Drafts posts and interacts with the LinkedIn API.' },
                        { title: 'Smart Home (AC/IR)', desc: 'Controls local IoT devices via IR bridges.' },
                        { title: 'Crypto & Stocks', desc: 'Live market analysis and portfolio tracking.' },
                        { title: 'GitHub Management', desc: 'Creates PRs, reads issues, and manages repos.' },
                    ].map((skill, i) => (
                        <div key={i} className="glass-panel skill-card">
                            <Activity className="skill-icon" size={24} />
                            <h4>{skill.title}</h4>
                            <p>{skill.desc}</p>
                        </div>
                    ))}
                </div>

                <div className="more-skills">
                    <Link to="/docs" className="btn btn-outline">Explore All Skills</Link>
                </div>
            </section>

            {/* Footer */}
            <footer className="footer">
                <div className="glass-panel footer-content">
                    <div className="footer-brand">
                        <Bot className="brand-icon" size={24} />
                        <span className="brand-text">Ninoclaw</span>
                    </div>
                    <p>© 2026 Siddhardha Devarakonda. All rights reserved.</p>
                </div>
            </footer>
        </div>
    );
}
