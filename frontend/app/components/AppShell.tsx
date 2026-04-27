'use client';

import React, { useEffect, useState } from 'react';
import { Activity, Cpu, Moon, ShieldCheck, Sun, TrendingUp } from 'lucide-react';
import Link from 'next/link';
import type { UserPersona } from '../types/persona';

const THEME_KEY = 'hpdc-theme-v2';

function getInitialTheme() {
  if (typeof window === 'undefined') return 'light';
  const storedTheme = window.localStorage.getItem(THEME_KEY);
  return storedTheme === 'light' || storedTheme === 'dark' ? storedTheme : 'light';
}

export default function AppShell({
  sidebar,
  children,
  persona,
  onChangePersona,
}: {
  sidebar: React.ReactNode;
  children: React.ReactNode;
  persona: UserPersona | null;
  onChangePersona: () => void;
}) {
  const [theme, setTheme] = useState<'light' | 'dark'>(getInitialTheme);

  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    window.localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">{theme === 'dark' ? 'Command deck intelligence' : 'Cinematic foundry intelligence'}</span>
          <strong>AlloyQuote Studio</strong>
        </div>
        <nav aria-label="Workflow">
          <Link href="/">
            <span style={{ cursor: 'pointer' }}>
              <Cpu size={15} />
              CAD Agent
            </span>
          </Link>
          <Link href="/market">
            <span style={{ cursor: 'pointer' }}>
              <TrendingUp size={15} />
              Market Intel
            </span>
          </Link>
          <span title="Source-aware discovery">
            <ShieldCheck size={15} />
            Agentic
          </span>
        </nav>
        <button className="persona-pill" type="button" onClick={onChangePersona}>
          {persona === 'technical' ? 'Technical view' : persona === 'nontechnical' ? 'Buyer view' : 'Choose view'}
        </button>
        <div className="theme-switch" aria-label="Theme switcher">
          <button
            type="button"
            className={theme === 'light' ? 'active' : ''}
            onClick={() => setTheme('light')}
          >
            <Sun size={15} />
            Dunkirk Light
          </button>
          <button
            type="button"
            className={theme === 'dark' ? 'active' : ''}
            onClick={() => setTheme('dark')}
          >
            <Moon size={15} />
            Starfleet Dark
          </button>
        </div>
      </header>
      <div className="main-container">
        <aside className="agent-pane">{sidebar}</aside>
        <section className="hud-pane">{children}</section>
      </div>
    </main>
  );
}
