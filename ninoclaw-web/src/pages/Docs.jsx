import { useState } from 'react';
import { Terminal, Cpu, Blocks, LayoutPanelLeft, Code, ChevronRight } from 'lucide-react';
import archImg from '../assets/architecture.png';
import './Docs.css';

export default function Docs() {
    const [activeTab, setActiveTab] = useState('quickstart');

    const content = {
        quickstart: (
            <div className="doc-content animate-fade-in">
                <h2>Quickstart Guide</h2>
                <p>Get Ninoclaw up and running on your local machine in minutes.</p>

                <h3>Prerequisites</h3>
                <ul>
                    <li>Python 3.10+</li>
                    <li>Node.js (for React/Expo builders)</li>
                    <li>A Telegram Bot Token (from BotFather)</li>
                </ul>

                <h3>Installation</h3>
                <div className="code-block">
                    <pre><code>{`git clone https://github.com/Devarakonda-Siddhardha/Ninoclaw.git
cd Ninoclaw
pip install -r requirements.txt
./ninoclaw setup
./ninoclaw start`}</code></pre>
                </div>

                <p>Once started, the local dashboard will be available at <code>http://localhost:8080</code> and the Telegram bot will come online.</p>
            </div>
        ),
        architecture: (
            <div className="doc-content animate-fade-in">
                <h2>Architecture Overview</h2>
                <div className="docs-hero-image">
                    <img src={archImg} alt="AI Routing Architecture" />
                </div>
                <p>Ninoclaw is designed as a centralized intelligence hub orchestrating multiple interfaces and models.</p>

                <div className="arch-grid">
                    <div className="glass-panel arch-card">
                        <h4><Cpu size={20} /> ai.py (Smart Routing)</h4>
                        <p>Routes prompts dynamically. Simple queries hit fast models (Gemini Flash), complex tool-requests hit reasoning models (OpenAI/Anthropic), and offline queries route to local Ollama.</p>
                    </div>
                    <div className="glass-panel arch-card">
                        <h4><LayoutPanelLeft size={20} /> dashboard.py</h4>
                        <p>A complete Flask-based local UI providing a visual interface over the SQLite memory database, allowing you to manage cron jobs, memory, and builds without Telegram.</p>
                    </div>
                    <div className="glass-panel arch-card">
                        <h4><Terminal size={20} /> telegram_bot.py</h4>
                        <p>The omnichannel gateway. Handles multimodal image queries, streaming Markdown responses, and recursive "Ralph-loop" self-correction when tools fail.</p>
                    </div>
                </div>
            </div>
        ),
        skills: (
            <div className="doc-content animate-fade-in">
                <h2>Available Skills & Builders</h2>
                <p>Ninoclaw ships with 29+ built-in autonomous skills. Here are the highlights:</p>

                <div className="skill-detail glass-panel">
                    <h3>Expo React Native Builder</h3>
                    <p>Scaffolds full iOS/Android apps using <code>npx create-expo-app</code>. It can edit components dynamically, capture screenshots of the running web preview, and read Metro logs to self-diagnose and fix compilation errors autonomously.</p>
                </div>

                <div className="skill-detail glass-panel">
                    <h3>React Web Builder</h3>
                    <p>Generates complex React frontends. It can receive mockup images via Telegram, write the corresponding React/Vanilla CSS code, and serve a live preview url natively from the dashboard.</p>
                </div>

                <div className="skill-detail glass-panel">
                    <h3>Ecosystem Integrations</h3>
                    <p>Includes native tools for <strong>LinkedIn</strong> (posting/messaging), <strong>GitHub</strong> (PRs/Issues), <strong>Spotify/YouTube Music</strong>, <strong>Crypto/Stocks</strong> tracking, and even Smart Home <strong>AC Control</strong> via localized IR bridges.</p>
                </div>
            </div>
        )
    };

    return (
        <div className="docs-container container">
            {/* Sidebar Navigation */}
            <aside className="docs-sidebar glass-panel">
                <h3>Documentation</h3>
                <nav className="docs-nav">
                    <button
                        className={`nav-btn ${activeTab === 'quickstart' ? 'active' : ''}`}
                        onClick={() => setActiveTab('quickstart')}
                    >
                        <Terminal size={18} /> Quickstart
                    </button>
                    <button
                        className={`nav-btn ${activeTab === 'architecture' ? 'active' : ''}`}
                        onClick={() => setActiveTab('architecture')}
                    >
                        <Blocks size={18} /> Architecture
                    </button>
                    <button
                        className={`nav-btn ${activeTab === 'skills' ? 'active' : ''}`}
                        onClick={() => setActiveTab('skills')}
                    >
                        <Code size={18} /> Skills & Builders
                    </button>
                </nav>
            </aside>

            {/* Main Content Area */}
            <main className="docs-main">
                {content[activeTab]}
            </main>
        </div>
    );
}
