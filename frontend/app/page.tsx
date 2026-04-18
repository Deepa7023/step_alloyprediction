'use client';

import React, { useEffect, useState } from 'react';
import AgentPane from './components/AgentPane';
import AppShell from './components/AppShell';
import DashboardHUD from './components/DashboardHUD';
import PersonaModal from './components/PersonaModal';
import type { AgentReport } from './types/report';
import type { UserPersona } from './types/persona';

export default function Home() {
  const [analysisData, setAnalysisData] = useState<AgentReport | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [persona, setPersona] = useState<UserPersona | null>(null);
  const [isPersonaLoaded, setIsPersonaLoaded] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => {
      const storedPersona = window.localStorage.getItem('hpdc-persona');
      if (storedPersona === 'nontechnical' || storedPersona === 'technical') {
        setPersona(storedPersona);
      }
      setIsPersonaLoaded(true);
    }, 0);

    return () => window.clearTimeout(timer);
  }, []);

  const handlePersonaSelect = (nextPersona: UserPersona) => {
    setPersona(nextPersona);
    window.localStorage.setItem('hpdc-persona', nextPersona);
  };

  return (
    <AppShell
      persona={persona}
      onChangePersona={() => setPersona(null)}
      sidebar={
        <AgentPane 
          persona={persona || 'nontechnical'}
          onAnalysisComplete={setAnalysisData} 
          setIsProcessing={setIsProcessing} 
        />
      }
    >
        <DashboardHUD 
          persona={persona || 'nontechnical'}
          data={analysisData} 
          isProcessing={isProcessing} 
        />
        {isPersonaLoaded && !persona && <PersonaModal onSelect={handlePersonaSelect} />}
    </AppShell>
  );
}
