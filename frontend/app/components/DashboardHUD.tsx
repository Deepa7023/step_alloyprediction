'use client';

import React from 'react';
import { motion } from 'framer-motion';
import { Activity, Bot, Box, CheckCircle2, Clock, Database, DollarSign, TrendingUp } from 'lucide-react';
import CADViewer from './CADViewer';
import ReportCharts from './ReportCharts';
import type { AgentReport } from '../types/report';
import type { UserPersona } from '../types/persona';

interface DashboardHUDProps {
  persona: UserPersona;
  data: AgentReport | null;
  isProcessing: boolean;
}

const money = (value?: number, currency = '$') => `${currency}${Number(value || 0).toFixed(2)}`;
const number = (value?: number, digits = 2) => Number(value || 0).toFixed(digits);
const priceValue = (value?: number | null) => (typeof value === 'number' ? money(value) : 'Unavailable');

export default function DashboardHUD({ persona, data, isProcessing }: DashboardHUDProps) {
  const isTechnical = persona === 'technical';

  if (!data && !isProcessing) {
    return (
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

  const report = data;
  const cost = report.cost_estimation;
  const traits = report.technical_matrix;
  const market = report.market_snapshot;
  const dimensions = traits.dimensions || {};
  const volumeCm3 = traits.volume / 1000;
  const surfaceCm2 = traits.surface_area / 100;

  return (
    <motion.section className="report" initial={{ opacity: 0, y: 18 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.45 }}>
      <motion.div className="report-header" initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
        <div>
          <p className="eyebrow">Completed quote</p>
          <h2>{report.file}</h2>
          <p className="subtle">Geometry engine: {report.engine}</p>
        </div>
        <div className="report-status">
          <CheckCircle2 size={18} />
          <span>Per-part cost ready</span>
        </div>
      </motion.div>

        <motion.div className="cost-hero" initial={{ opacity: 0, scale: 0.985 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.12 }}>
        <div>
          <p>Per part HPDC cost</p>
          <strong>{money(cost.per_part_cost ?? cost.total_unit_cost)}</strong>
          <span>INR {number(cost.unit_cost_inr, 2)} per part</span>
        </div>
        <div className="cost-range">
          <span>Expected fluctuation</span>
          <strong>{money(cost.fluctuation_range.min)} - {money(cost.fluctuation_range.max)}</strong>
          <small>Range includes {cost.fluctuation_range.percent}% metal and process variation.</small>
        </div>
      </motion.div>

      <div className="report-grid">
        {report.manufacturing_assumptions && (
          <motion.div className="metric-panel assumptions-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.16 }}>
            <div className="section-title">
              <Bot size={18} />
              <span>Agent-Decided Assumptions</span>
            </div>
            <p className="ai-summary">{report.manufacturing_assumptions.audience_summary}</p>
            <div className="assumption-grid">
              {report.manufacturing_assumptions.decisions.map((decision) => (
                <div key={decision.label}>
                  <span>{decision.label}</span>
                  <strong>{decision.value}</strong>
                  <small>{decision.reason}</small>
                </div>
              ))}
            </div>
            <div className="source-strip">
              <strong>Confidence {Math.round(report.manufacturing_assumptions.confidence * 100)}%</strong>
              <span>{report.manufacturing_assumptions.open_data_sources.join(' ')}</span>
            </div>
          </motion.div>
        )}

        <motion.div className="visual-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }}>
          <div className="section-title">
            <Box size={18} />
            <span>CAD Preview</span>
          </div>
          <CADViewer stlData={traits.preview_mesh} />
        </motion.div>

        <motion.div className="metric-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.22 }}>
          <div className="section-title">
            <Database size={18} />
            <span>{isTechnical ? 'Geometry Extracted From CAD' : 'Part Size Read From CAD'}</span>
          </div>
          <div className="metric-grid">
            <Metric label="Bounding box X" value={number(dimensions.x)} unit="mm" />
            <Metric label="Bounding box Y" value={number(dimensions.y)} unit="mm" />
            <Metric label="Bounding box Z" value={number(dimensions.z)} unit="mm" />
            <Metric label="Volume" value={number(volumeCm3)} unit="cm3" />
            <Metric label="Surface area" value={number(surfaceCm2)} unit="cm2" />
            <Metric label="Projected area" value={number(traits.projected_area)} unit="mm2" />
            <Metric label="Casting weight" value={number(cost.weight_g, 1)} unit="g" />
            <Metric label="Integrity score" value={number(traits.validation?.integrity_score, 0)} unit="/100" />
          </div>
        </motion.div>

        <motion.div className="metric-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.26 }}>
          <div className="section-title">
            <DollarSign size={18} />
            <span>Per Part Cost Breakdown</span>
          </div>
          <div className="breakdown-list">
            <CostLine label="Material" value={cost.material_cost} />
            <CostLine label="Machine and labour" value={cost.machine_cost} />
            <CostLine label="Die amortization" value={cost.amortization} />
            <CostLine label="HPDC port / finishing" value={cost.port_cost} />
          </div>
        </motion.div>

        <motion.div className="metric-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
          <div className="section-title">
            <TrendingUp size={18} />
            <span>Machine And Market</span>
          </div>
          <div className="metric-grid compact">
            <Metric label="Alloy" value={market.metal?.replaceAll('_', ' ') || 'Selected alloy'} unit="" />
            <Metric label="Live spot price" value={priceValue(market.live_spot_price_usd)} unit="/kg" />
            <Metric label="Reference spot price" value={priceValue(market.reference_price_usd)} unit="/kg" />
            <Metric label="Live location price" value={priceValue(market.live_location_adjusted_price_usd)} unit="/kg" />
            <Metric label="Reference location price" value={priceValue(market.reference_location_adjusted_price_usd)} unit="/kg" />
            <Metric label="Regional premium" value={number(market.regional_premium_percent, 2)} unit="%" />
            <Metric label="Freight estimate" value={money(market.estimated_freight_usd_per_kg)} unit="/kg" />
            <Metric label="Price source" value={market.price_source || 'REFERENCE'} unit="" />
            <Metric label="Price mode" value={market.is_live_metal_price ? 'Live market' : 'Live unavailable'} unit="" />
            <Metric label="Exchange" value={number(market.exchange_rate, 2)} unit="INR/USD" />
            <Metric label="Plant geodata" value={`${market.location_geodata?.lat ?? 'n/a'}, ${market.location_geodata?.lon ?? 'n/a'}`} unit="" />
            <Metric label="Selected machine" value={number(cost.machine_details.selected_machine, 0)} unit="T" />
            <Metric label="Required tonnage" value={number(cost.machine_details.required_tonnage, 1)} unit="T" />
            <Metric label="Cycle time" value={number(cost.machine_details.cycle_time_s, 1)} unit="s" />
            <Metric label="Shots per hour" value={number(cost.machine_details.shots_per_hour, 1)} unit="" />
            <Metric label="Tooling estimate" value={money(cost.tooling_estimate)} unit="" />
          </div>
        </motion.div>

        <motion.div className="metric-panel chart-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.31 }}>
          <div className="section-title">
            <TrendingUp size={18} />
            <span>Cost And Market Charts</span>
          </div>
          <ReportCharts report={report} />
        </motion.div>

        {market.location_price_table && (
          <motion.div className="metric-panel geo-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.32 }}>
            <div className="section-title">
              <TrendingUp size={18} />
              <span>Location-Wise Price Table</span>
            </div>
            <div className="geo-table">
              {market.location_price_table.map((row) => (
                <div key={row.name}>
                  <span>{row.name}</span>
                  <strong>{money(row.location_adjusted_usd_per_kg)} / kg</strong>
                  <em className={row.is_live_price ? 'price-badge live' : 'price-badge reference'}>
                    {row.is_live_price ? 'Live' : 'Reference'}
                  </em>
                  <small>
                    {row.city}, {row.country} / {row.lat}, {row.lon}
                  </small>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {report.ai_insight && (
          <motion.div className="metric-panel ai-panel" initial={{ opacity: 0, y: 16 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.34 }}>
            <div className="section-title">
              <Bot size={18} />
              <span>AI Quote Notes</span>
            </div>
            <p className="ai-summary">{report.ai_insight.summary}</p>
            <div className="ai-list">
              <strong>Key drivers</strong>
              {report.ai_insight.key_drivers.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
            <div className="ai-list">
              <strong>Risk notes</strong>
              {report.ai_insight.risk_notes.map((item) => (
                <span key={item}>{item}</span>
              ))}
            </div>
            <div className="recommendation">
              <strong>Recommendation</strong>
              <span>{report.ai_insight.recommendation}</span>
            </div>
            <small className="ai-source-line">
              Provider: {report.ai_insight.provider}
              {report.ai_insight.model ? ` / ${report.ai_insight.model}` : ''}
              {report.ai_insight.sources.length ? ` / ${report.ai_insight.sources.length} web sources` : ''}
            </small>
          </motion.div>
        )}
      </div>

      <motion.div className="market-footer" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
        <Clock size={16} />
        <span>
          Price source: {market.price_source || 'REFERENCE'}.
          {market.pricing_note ? ` ${market.pricing_note}` : ''}
          {market.provider_error ? ` Provider message: ${market.provider_error}` : ''}
        </span>
      </motion.div>
    </motion.section>
  );
}

function Metric({ label, value, unit }: { label: string; value: string; unit: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>
        {value} {unit && <small>{unit}</small>}
      </strong>
    </div>
  );
}

function CostLine({ label, value }: { label: string; value: number }) {
  return (
    <div className="cost-line">
      <span>{label}</span>
      <strong>{money(value)}</strong>
    </div>
  );
}
