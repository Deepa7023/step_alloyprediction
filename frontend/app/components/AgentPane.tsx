'use client';

import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import gsap from 'gsap';
import { motion } from 'framer-motion';
import { Bot, Calculator, Factory, FileUp, Loader2, MapPin, Package, SlidersHorizontal } from 'lucide-react';
import type { AgentReport } from '../types/report';
import type { UserPersona } from '../types/persona';

interface AgentPaneProps {
  persona: UserPersona;
  onAnalysisComplete: (data: AgentReport) => void;
  setIsProcessing: (loading: boolean) => void;
}

interface PlantLocation {
  name: string;
  multiplier: number;
  city?: string;
  currency?: string;
}

interface MetalRate {
  current_price: number;
  label?: string;
  source?: string;
  status?: string;
}

interface ProviderStatus {
  configured: boolean;
  model?: string;
  role: string;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5000';

const fallbackLocations: PlantLocation[] = [
  { name: 'India (Pune Node)', multiplier: 0.82, city: 'Pune', currency: 'INR' },
  { name: 'India (Chennai Cluster)', multiplier: 0.85, city: 'Chennai', currency: 'INR' },
  { name: 'China (Ningbo Hub)', multiplier: 0.92, city: 'Ningbo', currency: 'CNY' },
  { name: 'Germany (Stuttgart)', multiplier: 1.7, city: 'Stuttgart', currency: 'EUR' },
];

const fallbackMetals: Record<string, MetalRate> = {
  Aluminum_A380: { current_price: 2.85, label: 'Aluminum A380' },
  Zinc_ZD3: { current_price: 3.42, label: 'Zinc ZD3 / Zamak' },
  Magnesium_AZ91D: { current_price: 4.65, label: 'Magnesium AZ91D' },
};

const supportedExtensions = ['STEP', 'STP', 'IGES', 'IGS', 'STL', 'OBJ', 'PLY', 'GLB', 'GLTF', '3MF', 'OFF', 'DAE'];
const acceptExtensions = supportedExtensions.map((extension) => `.${extension.toLowerCase()}`).join(',');

export default function AgentPane({ persona, onAnalysisComplete, setIsProcessing }: AgentPaneProps) {
  const [file, setFile] = useState<File | null>(null);
  const [locations, setLocations] = useState<PlantLocation[]>(fallbackLocations);
  const [metals, setMetals] = useState<Record<string, MetalRate>>(fallbackMetals);
  const [selectedLocation, setSelectedLocation] = useState<PlantLocation>(fallbackLocations[0]);
  const [metal, setMetal] = useState('AUTO');
  const [pieces, setPieces] = useState('');
  const [sliders, setSliders] = useState('');
  const [portCost, setPortCost] = useState('');
  const [statusText, setStatusText] = useState('Upload CAD. The agent will infer alloy, pieces, sliders, and finishing assumptions.');
  const [error, setError] = useState('');
  const [marketNote, setMarketNote] = useState('');
  const [aiProviders, setAiProviders] = useState<Record<string, ProviderStatus>>({});
  const fileInputRef = useRef<HTMLInputElement>(null);
  const sparkleRef = useRef<HTMLDivElement>(null);
  const isTechnical = persona === 'technical';

  useEffect(() => {
    async function loadStartupData() {
      try {
        const response = await axios.get(`${API_URL}/api/market-data`);
        setLocations(response.data.plant_locations || fallbackLocations);
        setMetals(response.data.current_base_rates || fallbackMetals);
        setMarketNote(response.data.pricing_note || '');
      } catch {
        setMarketNote('Market service is offline. Reference alloy rates are shown until the API is reachable.');
      }

      try {
        const response = await axios.get(`${API_URL}/api/ai/status`);
        setAiProviders(response.data.providers || {});
      } catch {
        setAiProviders({});
      }
    }

    loadStartupData();
  }, []);

  useEffect(() => {
    if (!sparkleRef.current) return;

    const particles = sparkleRef.current.querySelectorAll('.spark-particle');
    const animation = gsap.to(particles, {
      x: () => gsap.utils.random(-18, 18),
      y: () => gsap.utils.random(-20, 22),
      opacity: () => gsap.utils.random(0.2, 0.9),
      scale: () => gsap.utils.random(0.7, 1.4),
      duration: () => gsap.utils.random(1.4, 2.8),
      repeat: -1,
      yoyo: true,
      stagger: 0.12,
      ease: 'sine.inOut',
    });

    return () => {
      animation.kill();
    };
  }, []);

  const submit = async () => {
    if (!file) {
      setError('Please upload a CAD file first.');
      return;
    }

    setError('');
    setIsProcessing(true);
    setStatusText('Extracting bounding box, volume, surface area, and projected area from CAD...');

    const body = new FormData();
    body.append('file', file);
    if (metal !== 'AUTO') body.append('metal', metal);
    if (pieces) body.append('annual_volume', String(Math.max(1, Number(pieces))));
    body.append('location_name', selectedLocation.name);
    if (sliders) body.append('sliders', String(Math.max(0, Number(sliders))));
    if (portCost) body.append('port_cost', String(Math.max(0, Number(portCost))));

    try {
      const response = await axios.post(`${API_URL}/api/agent/process`, body);
      onAnalysisComplete(response.data.agent_report);
      setStatusText('Per-part HPDC estimate is ready.');
    } catch (err: unknown) {
      const detail = axios.isAxiosError(err)
        ? err.response?.data?.detail || 'Estimation failed. Please check the CAD file and backend service.'
        : 'Estimation failed. Please check the CAD file and backend service.';
      setError(detail);
      setStatusText('The agent could not complete this estimate.');
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <motion.section
      className="intake"
      initial={{ opacity: 0, x: -18 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.55, ease: 'easeOut' }}
    >
      <div className="spark-layer" ref={sparkleRef} aria-hidden="true">
        {Array.from({ length: 14 }).map((_, index) => (
          <span key={index} className="spark-particle" />
        ))}
      </div>

      <motion.div className="brand-block" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
        <div className="brand-mark">
          <Bot size={22} />
        </div>
        <div>
          <p className="eyebrow">{isTechnical ? 'Engineer costing console' : 'HPDC Cost Agent'}</p>
          <h1>{isTechnical ? 'CAD-driven HPDC estimator' : 'Upload CAD. Get a plain quote.'}</h1>
          <p className="lede">
            {isTechnical
              ? 'Review inferred assumptions, override process inputs, and inspect geometry-driven cost results.'
              : 'The agent reads geometry, infers practical assumptions, and explains the per-part estimate for non-technical review.'}
          </p>
        </div>
      </motion.div>

      <motion.div className="status-strip" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}>
        <Calculator size={18} />
        <span>{statusText}</span>
      </motion.div>

      <motion.div className="form-stack" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.24 }}>
        <div className="field-block upload-block">
          <label>CAD file</label>
          <input
            ref={fileInputRef}
            type="file"
            accept={acceptExtensions}
            onChange={(event) => {
              const nextFile = event.target.files?.[0] || null;
              setFile(nextFile);
              setStatusText(nextFile ? `${nextFile.name} selected. Add quote inputs and run estimation.` : statusText);
            }}
            hidden
          />
          <button className="upload-button" type="button" onClick={() => fileInputRef.current?.click()}>
            <FileUp size={20} />
            <span>{file ? file.name : 'Upload CAD file'}</span>
          </button>
          <p className="supported-copy">{supportedExtensions.join(' / ')}</p>
        </div>

        <div className="field-block">
          <label htmlFor="plant">Where should this be manufactured?</label>
          <div className="input-with-icon">
            <MapPin size={18} />
            <select
              id="plant"
              value={selectedLocation.name}
              onChange={(event) => {
                const next = locations.find((location) => location.name === event.target.value);
                if (next) setSelectedLocation(next);
              }}
            >
              {locations.map((location) => (
                <option key={location.name} value={location.name}>
                  {location.name}
                </option>
              ))}
            </select>
          </div>
          <p className="supported-copy">
            Everything else is inferred from the CAD file. Use advanced overrides only when you already know the commercial assumptions.
          </p>
        </div>

        <details className="advanced-panel" open={isTechnical}>
          <summary>Advanced overrides</summary>
          <div className="field-grid">
          <div className="field-block">
            <label htmlFor="metal">Alloy type</label>
            <div className="input-with-icon">
              <Factory size={18} />
              <select id="metal" value={metal} onChange={(event) => setMetal(event.target.value)}>
                <option value="AUTO">Auto from CAD / default</option>
                {Object.entries(metals).map(([key, rate]) => (
                  <option key={key} value={key}>
                    {rate.label || key.replaceAll('_', ' ')}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="field-block">
            <label htmlFor="pieces">Pieces per year</label>
            <div className="input-with-icon">
              <Package size={18} />
              <input
                id="pieces"
                type="number"
                min={1}
                placeholder="Auto"
                value={pieces}
                onChange={(event) => setPieces(event.target.value)}
              />
            </div>
          </div>

          <div className="field-block">
            <label htmlFor="sliders">Sliders in die</label>
            <div className="input-with-icon">
              <SlidersHorizontal size={18} />
              <input
                id="sliders"
                type="number"
                min={0}
                placeholder="Auto"
                value={sliders}
                onChange={(event) => setSliders(event.target.value)}
              />
            </div>
          </div>

          <div className="field-block">
            <label htmlFor="portCost">Port / finishing cost</label>
            <div className="input-with-icon">
              <Calculator size={18} />
              <input
                id="portCost"
                type="number"
                min={0}
                step={0.1}
                placeholder="Auto"
                value={portCost}
                onChange={(event) => setPortCost(event.target.value)}
              />
            </div>
          </div>
          </div>
        </details>

        <div className="quote-preview">
          <div>
            <span>Assumption mode</span>
            <strong>CAD assisted</strong>
          </div>
          <div>
            <span>Plant</span>
            <strong>{selectedLocation.city || selectedLocation.name}</strong>
          </div>
          <div>
            <span>Overrides</span>
            <strong>{[metal !== 'AUTO', pieces, sliders, portCost].filter(Boolean).length}</strong>
          </div>
        </div>

        <div className="provider-strip">
          {['groq', 'firecrawl', 'tinyfish'].map((provider) => (
            <div key={provider} className={aiProviders[provider]?.configured ? 'provider-on' : 'provider-off'}>
              <span>{provider}</span>
              <strong>{aiProviders[provider]?.configured ? 'connected' : 'add key'}</strong>
            </div>
          ))}
        </div>

        {marketNote && <p className="note">{marketNote}</p>}
        {error && <p className="error-text">{error}</p>}

        <button className="primary-action" type="button" onClick={submit}>
          <Loader2 className="loading-icon" size={18} />
          Run per-part estimation
        </button>
      </motion.div>
    </motion.section>
  );
}
