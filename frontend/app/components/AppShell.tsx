'use client';

import React, { useEffect, useState } from 'react';
import { Activity, Cpu, Moon, ShieldCheck, Sun } from 'lucide-react';
import type { UserPersona } from '../types/persona';

function getInitialTheme() {
  if (typeof window === 'undefined') return 'dark';
  const storedTheme = window.localStorage.getItem('hpdc-theme');
  return storedTheme === 'light' || storedTheme === 'dark' ? storedTheme : 'dark';
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
    window.localStorage.setItem('hpdc-theme', theme);
  }, [theme]);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <span className="eyebrow">{theme === 'dark' ? 'Command deck intelligence' : 'Cinematic foundry intelligence'}</span>
          <strong>AlloyQuote Studio</strong>
        </div>
        <nav aria-label="Workflow">
          <span>
            <Cpu size={15} />
            CAD
          </span>
          <span>
            <Activity size={15} />
            Cost
          </span>
          <span>
            <ShieldCheck size={15} />
            Source-aware
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
