'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { BriefcaseBusiness, Wrench } from 'lucide-react';
import type { UserPersona } from '../types/persona';

export default function PersonaModal({ onSelect }: { onSelect: (persona: UserPersona) => void }) {
  return (
    <motion.div className="persona-backdrop" initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}>
      <motion.section
        className="persona-modal"
        initial={{ opacity: 0, y: 18, scale: 0.98 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.35 }}
      >
        <p className="eyebrow">Choose your view</p>
        <h2>How should AlloyQuote explain the estimate?</h2>
        <p>
          Pick the version that matches the person reading the quote. You can still access the same CAD analysis and pricing logic.
        </p>

        <div className="persona-grid">
          <button type="button" onClick={() => onSelect('nontechnical')}>
            <BriefcaseBusiness size={24} />
            <strong>Non-technical buyer</strong>
            <span>Plain language, fewer controls, clear assumptions, quote-first output.</span>
          </button>
          <button type="button" onClick={() => onSelect('technical')}>
            <Wrench size={24} />
            <strong>Technical engineer</strong>
            <span>CAD metrics, process assumptions, advanced overrides, deeper costing detail.</span>
          </button>
        </div>
      </motion.section>
    </motion.div>
  );
}
