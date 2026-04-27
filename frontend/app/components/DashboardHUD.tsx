'use client';

import { motion } from 'framer-motion';
import { Activity, Bot, Box, CheckCircle2, Clock, Database, DollarSign, TrendingUp } from 'lucide-react';
import { useState } from 'react';
import AlloyBot from './AlloyBot';
import CADViewer from './CADViewer';
import ReportCharts from './ReportCharts';
import type { AgentReport } from '../types/report';
import type { UserPersona } from '../types/persona';

const CURRENCIES = ['USD', 'INR', 'EUR', 'CNY', 'GBP'] as const;
type Currency = typeof CURRENCIES[number];
const SYMBOLS: Record<Currency, string> = { USD: '$', INR: '₹', EUR: '€', CNY: '¥', GBP: '£' };

interface DashboardHUDProps {
  persona: UserPersona;
  data: AgentReport | null;
  isProcessing: boolean;
}

const fmt = (value: number, sym: string) => `${sym}${Number(value || 0).toFixed(2)}`;
const number = (value?: number, digits = 2) => Number(value || 0).toFixed(digits);

export default function DashboardHUD({ persona, data, isProcessing }: DashboardHUDProps) {
  const [currency, setCurrency] = useState<Currency>('INR');
  const isTechnical = persona === 'technical';

  if (!data && !isProcessing) {
    return (
      <>
        <motion.section className="empty-state hero-state no-visual" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.55 }}>
          <div className="hero-copy">
            <Activity size={36} />
            <p className="eyebrow">Real CAD intelligence</p>
            <h2>{isTechnical ? 'Ready for CAD and process inference' : 'Upload CAD to see the real part'}</h2>
            <p>
              {isTechnical
                ? 'Upload STEP, IGES, STL, OBJ or other supported CAD. The technical view keeps process assumptions and geometry metrics visible.'
                : 'No synthetic figure is shown before upload. The report renders only the mesh extracted from your CAD file, then explains the estimate in plain language.'}
            </p>
          </div>
        </motion.section>
        <AlloyBot reportContext={null} />
      </>
    );
  }

  if (isProcessing) {
    return (
      <motion.section className="empty-state processing-state" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.35 }}>
        <div className="spinner" />
        <h2>Building quote</h2>
        <p>Reading CAD geometry, checking alloy price, and calculating per-part HPDC cost.</p>
      </motion.section>
    );
  }

  if (!data) return null;

  const cost = data.cost_estimation;
  const traits = data.technical_matrix;
  const market = data.market_snapshot;
  const dimensions = traits.dimensions || {};
  const volumeCm3 = traits.volume / 1000;
  const surfaceCm2 = traits.surface_area / 100;

  const fx: Record<string, number> = (market as Record<string, unknown>).fx_rates as Record<string, number> || { USD: 1, INR: 83.5, EUR: 0.92, CNY: 7.24, GBP: 0.79 };
  const rate = fx[currency] ?? 1;
  const sym = SYMBOLS[currency];

  const perPart = (cost.per_part_cost ?? cost.total_unit_cost ?? 0) * rate;
  const flucPct = cost.fluctuation_range?.percent ?? 5;
  const perPartLow = perPart * (1 - flucPct / 100);
  const perPartHigh = perPart * (1 + flucPct / 100);

  const spotPrice = (market.live_spot_price_usd ?? market.reference_price_usd ?? 0) * rate;
  const locationPrice = (market.live_location_adjusted_price_usd ?? market.reference_location_adjusted_price_usd ?? 0) * rate;

  const botContext = {
    report_id: data.id,
    file: data.file,
    engine: data.engine,
    geometry: {
      dimensions_mm: traits.dimensions,
      volume_cm3: volumeCm3,
      surface_area_cm2: surfaceCm2,
      projected_area_mm2: traits.projected_area,
      topology: traits.topology,
      validation: traits.validation,
    },
    manufacturing: {
      assumptions: data.manufacturing_assumptions?.decisions,
      confidence: data.manufacturing_assumptions?.confidence,
      summary: data.manufacturing_assumptions?.audience_summary,
      location: data.manufacturing_assumptions?.location || market.location,
    },
    cost: {
      total_unit_cost_usd: cost.total_unit_cost,
      per_part_cost_usd: cost.per_part_cost ?? cost.total_unit_cost,
      material_cost_usd: cost.material_cost,
      machine_cost_usd: cost.machine_cost,
      die_amortization_usd: cost.amortization,
      finishing_cost_usd: cost.port_cost,
      weight_g: cost.weight_g,
      tooling_estimate_usd: cost.tooling_estimate,
      selected_machine_tons: cost.machine_details?.selected_machine,
      cycle_time_s: cost.machine_details?.cycle_time_s,
      shots_per_hour: cost.machine_details?.shots_per_hour,
    },
    market: {
      alloy: market.metal,
      price_source: market.price_source,
      price_status: market.price_status,
      price_as_of: market.price_as_of,
      spot_price_usd_per_kg: market.live_spot_price_usd ?? market.reference_price_usd,
      location_adjusted_usd_per_kg: market.live_location_adjusted_price_usd ?? market.reference_location_adjusted_price_usd,
      regional_premium_percent: market.regional_premium_percent,
      freight_usd_per_kg: market.estimated_freight_usd_per_kg,
      plant_location: market.location_geodata,
    },
    ai_notes: data.ai_insight ? {
      summary: data.ai_insight.summary,
      key_drivers: data.ai_insight.key_drivers,
      risk_notes: data.ai_insight.risk_notes,
      recommendation: data.ai_insight.recommendation,
    } : undefined,
  };

  return (
    <>
      <motion.section className="report" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>

        {/* Header */}
        <motion.div className="report-header" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
          <div>
            <p className="eyebrow">Completed quote</p>
            <h2>{data.file}</h2>
            <p className="subtle">Geometry engine: {data.engine}</p>
          </div>
          <div className="report-status">
            <CheckCircle2 size={18} />
            <span>Per-part cost ready</span>
          </div>
        </motion.div>

        {/* Currency Switcher */}
        <motion.div className="currency-switcher" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.08 }}>
          <span className="currency-label">Display currency</span>
          <div className="currency-tabs">
            {CURRENCIES.map((c) => (
              <button
                key={c}
                type="button"
                className={`currency-tab ${currency === c ? 'active' : ''}`}
                onClick={() => setCurrency(c)}
              >
                {SYMBOLS[c]} {c}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Cost Hero */}
        <motion.div className="cost-hero" initial={{ opacity: 0, scale: 0.985 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.12 }}>
          <div>
            <p>Per part HPDC cost (Estimated)</p>
            <strong>{fmt(perPart, sym)}</strong>
            <span>≈ {fmt((cost.per_part_cost ?? cost.total_unit_cost ?? 0), '$')} per part (USD basis)</span>
          </div>
          <div className="cost-range">
            <span>Expected fluctuation</span>
            <strong>{fmt(perPartLow, sym)} — {fmt(perPartHigh, sym)}</strong>
            <small>Range includes {flucPct}% metal and process variation.</small>
          </div>
        </motion.div>

        <div className="report-grid">
          {/* Agent Assumptions */}
          {data.manufacturing_assumptions && (
            <motion.div className="metric-panel assumptions-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}>
              <div className="section-title"><Bot size={18} /><span>Agent-Decided Assumptions</span></div>
              <p className="ai-summary">{data.manufacturing_assumptions.audience_summary}</p>
              <div className="assumption-grid">
                {data.manufacturing_assumptions.decisions.map((decision) => (
                  <div key={decision.label}>
                    <span>{decision.label}</span>
                    <strong>{decision.value}</strong>
                    <small>{decision.reason}</small>
                  </div>
                ))}
              </div>
              <div className="source-strip">
                <strong>Confidence {Math.round(data.manufacturing_assumptions.confidence * 100)}%</strong>
                <span>{data.manufacturing_assumptions.open_data_sources.join(' ')}</span>
              </div>
            </motion.div>
          )}

          {/* CAD Viewer */}
          <motion.div className="visual-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}>
            <div className="section-title"><Box size={18} /><span>CAD Preview</span></div>
            <CADViewer
              stlData={traits.preview_mesh}
              diagnostics={{
                file: data.file,
                engine: data.engine,
                dimensions: traits.dimensions,
                volume: traits.volume,
                surfaceArea: traits.surface_area,
                projectedArea: traits.projected_area,
                topology: traits.topology,
                validation: traits.validation,
              }}
            />
          </motion.div>

          {/* Geometry Metrics */}
          <motion.div className="metric-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.22 }}>
            <div className="section-title">
              <Database size={18} />
              <span>{isTechnical ? 'Geometry Extracted From CAD' : 'Part Size Read From CAD'}</span>
            </div>
            <div className="metric-grid">
              <Metric label="Bounding box X" value={number(dimensions.x)} unit="mm" />
              <Metric label="Bounding box Y" value={number(dimensions.y)} unit="mm" />
              <Metric label="Bounding box Z" value={number(dimensions.z)} unit="mm" />
              <Metric label="Volume" value={number(volumeCm3)} unit="cm³" />
              <Metric label="Surface area" value={number(surfaceCm2)} unit="cm²" />
              <Metric label="Projected area" value={number(traits.projected_area)} unit="mm²" />
              <Metric label="Casting weight" value={number(cost.weight_g, 1)} unit="g" />
              <Metric label="Integrity score" value={number(traits.validation?.integrity_score, 0)} unit="/100" />
            </div>
          </motion.div>

          {/* Cost Breakdown */}
          <motion.div className="metric-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.26 }}>
            <div className="section-title">
              <DollarSign size={18} />
              <span>Per Part Cost Breakdown ({sym})</span>
            </div>
            <div className="breakdown-list">
              <CostLine label="Material" value={cost.material_cost} rate={rate} sym={sym} />
              <CostLine label="Machine and labour" value={cost.machine_cost} rate={rate} sym={sym} />
              <CostLine label="Die amortization" value={cost.amortization} rate={rate} sym={sym} />
              <CostLine label="HPDC port / finishing" value={cost.port_cost} rate={rate} sym={sym} />
            </div>
          </motion.div>

          {/* Machine & Market */}
          <motion.div className="metric-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
            <div className="section-title"><TrendingUp size={18} /><span>Machine And Market</span></div>
            <div className="metric-grid compact">
              <Metric label="Alloy" value={market.metal?.replaceAll('_', ' ') || 'Selected'} unit="" />
              <Metric label={market.is_live_metal_price ? 'Live spot price' : 'Reference spot'} value={fmt(spotPrice, sym)} unit="/kg" />
              <Metric label={market.is_live_metal_price ? 'Live location price' : 'Reference location'} value={fmt(locationPrice, sym)} unit="/kg" />
              <Metric label="Regional premium" value={number(market.regional_premium_percent, 2)} unit="%" />
              <Metric label="Freight estimate" value={fmt((market.estimated_freight_usd_per_kg || 0) * rate, sym)} unit="/kg" />
              <Metric label="Price mode" value={market.is_live_metal_price ? 'Live market' : 'Reference'} unit="" />
              <Metric label="Exchange rate" value={`${sym}${(rate).toFixed(4)}`} unit="/USD" />
              <Metric label="Selected machine" value={number(cost.machine_details?.selected_machine, 0)} unit="T" />
              <Metric label="Cycle time" value={number(cost.machine_details?.cycle_time_s, 1)} unit="s" />
              <Metric label="Shots per hour" value={number(cost.machine_details?.shots_per_hour, 1)} unit="" />
              <Metric label="Tooling estimate" value={fmt((cost.tooling_estimate || 0) * rate, sym)} unit="" />
              <Metric label="Plant location" value={`${market.location_geodata?.city ?? 'n/a'}, ${market.location_geodata?.country ?? ''}`} unit="" />
            </div>
          </motion.div>

          {/* Charts */}
          <motion.div className="metric-panel chart-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.31 }}>
            <div className="section-title"><TrendingUp size={18} /><span>Cost And Market Charts</span></div>
            <ReportCharts report={data} />
          </motion.div>

          {/* Location Price Table */}
          {market.location_price_table && (
            <motion.div className="metric-panel geo-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.32 }}>
              <div className="section-title"><TrendingUp size={18} /><span>Location-Wise Price Table ({sym})</span></div>
              <div className="geo-table">
                {market.location_price_table.map((row) => {
                  const pbc = (row as Record<string, unknown>).prices_by_currency as Record<string, number> | undefined;
                  const p = pbc ? (pbc[currency] ?? row.location_adjusted_usd_per_kg * rate) : row.location_adjusted_usd_per_kg * rate;
                  return (
                    <div key={row.name}>
                      <span>{row.name}</span>
                      <strong>{fmt(p, sym)} / kg</strong>
                      <em className={row.is_live_price ? 'price-badge live' : 'price-badge reference'}>
                        {row.is_live_price ? 'Live' : 'Reference'}
                      </em>
                      <small>{row.city}, {row.country}</small>
                    </div>
                  );
                })}
              </div>
            </motion.div>
          )}

          {/* AI Insight */}
          {data.ai_insight && (
            <motion.div className="metric-panel ai-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.34 }}>
              <div className="section-title"><Bot size={18} /><span>AI Quote Notes</span></div>
              <p className="ai-summary">{data.ai_insight.summary}</p>
              <div className="ai-list">
                <strong>Key drivers</strong>
                {data.ai_insight.key_drivers.map((item) => <span key={item}>{item}</span>)}
              </div>
              <div className="ai-list">
                <strong>Risk notes</strong>
                {data.ai_insight.risk_notes.map((item) => <span key={item}>{item}</span>)}
              </div>
              <div className="recommendation">
                <strong>Recommendation</strong>
                <span>{data.ai_insight.recommendation}</span>
              </div>
              <small className="ai-source-line">
                Provider: {data.ai_insight.provider}
                {data.ai_insight.model ? ` / ${data.ai_insight.model}` : ''}
                {data.ai_insight.sources?.length ? ` / ${data.ai_insight.sources.length} web sources` : ''}
              </small>
            </motion.div>
          )}
        </div>

        <motion.div className="market-footer" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
          <Clock size={16} />
          <span>
            Price source: {market.price_source || 'REFERENCE'}.
            {market.pricing_note ? ` ${market.pricing_note}` : ''}
          </span>
        </motion.div>
      </motion.section>

      <AlloyBot reportContext={botContext} />
    </>
  );
}

function Metric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value} {unit && <small>{unit}</small>}</strong>
    </div>
  );
}

function CostLine({ label, value, rate, sym }: { label: string; value: number; rate: number; sym: string }) {
  return (
    <div className="cost-line">
      <span>{label}</span>
      <strong>{sym}{((value || 0) * rate).toFixed(2)}</strong>
    </div>
  );
}
