'use client';

import React, { useCallback, useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';
import ReactECharts from 'echarts-for-react';
import axios from 'axios';
import { motion, AnimatePresence } from 'framer-motion';
import { Activity, ArrowDownRight, ArrowLeft, ArrowUpRight, Clock, RefreshCw, Sparkles, TrendingUp } from 'lucide-react';
import Link from 'next/link';

interface MarketPoint { timestamp: number; metal: string; price_usd: number; exchange_rate: number; }
interface FxData { rates: Record<string, number>; symbols: Record<string, string>; source: string; as_of: string; }
interface MarketRate { current_price: number; label?: string; family?: string; is_live?: boolean; status?: string; source?: string; notes?: string; }

const API_URL = process.env.NEXT_PUBLIC_API_URL || '';
const CURRENCIES = ['USD', 'INR', 'EUR', 'CNY', 'GBP'] as const;
type Cur = typeof CURRENCIES[number];
const SYM: Record<Cur, string> = { USD: '$', INR: '₹', EUR: '€', CNY: '¥', GBP: '£' };
const fmt = (n: number, sym: string) => `${sym}${n.toFixed(2)}`;
const formatTime = (ts: number) =>
  new Intl.DateTimeFormat('en-IN', {
    timeZone: 'Asia/Kolkata', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
  }).format(new Date(ts * 1000));

const FALLBACK_METALS = [
  { key: 'Aluminum_A380',   name: 'Aluminum A380',    color: '#10b981', gradA: '#10b981', gradB: '#059669' },
  { key: 'Zinc_ZD3',        name: 'Zinc ZD3 / Zamak', color: '#f59e0b', gradA: '#f59e0b', gradB: '#d97706' },
  { key: 'Magnesium_AZ91D', name: 'Magnesium AZ91D',  color: '#6366f1', gradA: '#6366f1', gradB: '#4f46e5' },
];
const PALETTE = ['#10b981', '#f59e0b', '#6366f1', '#06b6d4', '#ef4444', '#84cc16', '#14b8a6', '#a855f7', '#64748b', '#f97316'];

function PriceTicker({ label, value, prev, sym }: { label: string; value: number; prev: number; sym: string }) {
  const up = value >= prev;
  const delta = ((value - prev) / (prev || 1)) * 100;
  return (
    <motion.div
      className="ticker-card"
      animate={{ borderColor: up ? 'rgba(16,185,129,0.5)' : 'rgba(239,68,68,0.5)' }}
      transition={{ duration: 0.4 }}
    >
      <span className="ticker-label">{label}</span>
      <motion.strong
        key={value.toFixed(4)}
        className="ticker-value"
        initial={{ opacity: 0, y: up ? 6 : -6 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.28 }}
      >
        {fmt(value, sym)}<small>/kg</small>
      </motion.strong>
      <span className={`ticker-delta ${up ? 'up' : 'down'}`}>
        {up ? <ArrowUpRight size={13} /> : <ArrowDownRight size={13} />}
        {Math.abs(delta).toFixed(3)}%
      </span>
    </motion.div>
  );
}

/* ── D3 sparkline ────────────────────────────────────────── */
function D3Sparkline({ data, color, width = 120, height = 36 }: {
  data: number[]; color: string; width?: number; height?: number;
}) {
  const ref = useRef<SVGSVGElement>(null);
  useEffect(() => {
    if (!ref.current || data.length < 2) return;
    const svg = d3.select(ref.current);
    svg.selectAll('*').remove();
    const xScale = d3.scaleLinear().domain([0, data.length - 1]).range([2, width - 2]);
    const yScale = d3.scaleLinear().domain([d3.min(data) ?? 0, d3.max(data) ?? 1]).range([height - 4, 4]);
    const area = d3.area<number>()
      .x((_, i) => xScale(i))
      .y0(height)
      .y1((d) => yScale(d))
      .curve(d3.curveCatmullRom);
    const line = d3.line<number>()
      .x((_, i) => xScale(i))
      .y((d) => yScale(d))
      .curve(d3.curveCatmullRom);
    const grad = svg.append('defs').append('linearGradient')
      .attr('id', `sg-${color.replace('#', '')}`)
      .attr('x1', '0').attr('y1', '0').attr('x2', '0').attr('y2', '1');
    grad.append('stop').attr('offset', '0%').attr('stop-color', color).attr('stop-opacity', 0.35);
    grad.append('stop').attr('offset', '100%').attr('stop-color', color).attr('stop-opacity', 0);
    svg.append('path').datum(data).attr('d', area).attr('fill', `url(#sg-${color.replace('#', '')})`);
    svg.append('path').datum(data).attr('d', line)
      .attr('fill', 'none').attr('stroke', color).attr('stroke-width', 2).attr('stroke-linecap', 'round');
    const last = data[data.length - 1];
    svg.append('circle')
      .attr('cx', xScale(data.length - 1)).attr('cy', yScale(last)).attr('r', 3.5)
      .attr('fill', color).attr('stroke', 'var(--surface)').attr('stroke-width', 1.5);
  }, [data, color, width, height]);
  return <svg ref={ref} width={width} height={height} style={{ display: 'block' }} />;
}

/* ── Sparkle overlay ─────────────────────────────────────── */
function SparkleOverlay({ active }: { active: boolean }) {
  const DOTS = Array.from({ length: 18 }, (_, i) => ({
    left: `${(i * 37 + 11) % 100}%`,
    top:  `${(i * 53 + 7)  % 100}%`,
    delay: `${(i * 0.17) % 1.6}s`,
    size: i % 3 === 0 ? 4 : i % 3 === 1 ? 6 : 3,
  }));
  if (!active) return null;
  return (
    <div className="sparkle-canvas" aria-hidden>
      {DOTS.map((d, i) => (
        <span key={i} className="sparkle-dot" style={{ left: d.left, top: d.top, animationDelay: d.delay, width: d.size, height: d.size }} />
      ))}
    </div>
  );
}


export default function MarketIntel() {
  const [history, setHistory]   = useState<MarketPoint[]>([]);
  const [fx, setFx]             = useState<FxData | null>(null);
  const [currency, setCurrency] = useState<Cur>('INR');
  const [metalRates, setMetalRates] = useState<Record<string, MarketRate>>({});
  const [loading, setLoading]   = useState(true);
  const [lastSync, setLastSync] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const mountedRef = useRef(true);

  const rate = fx?.rates?.[currency] ?? 1;
  const sym  = SYM[currency];
  const metals = Object.keys(metalRates).length
    ? Object.entries(metalRates).map(([key, data], index) => {
        const color = PALETTE[index % PALETTE.length];
        return { key, name: data.label || key.replaceAll('_', ' '), color, gradA: color, gradB: color, rate: data };
      })
    : FALLBACK_METALS.map((m) => ({ ...m, rate: undefined as MarketRate | undefined }));

  const fetchAll = useCallback(async (showSpin = false) => {
    if (showSpin) setRefreshing(true);
    try {
      const [hRes, fRes, mRes] = await Promise.all([
        axios.get<{ history: MarketPoint[] }>(`${API_URL}/api/market-history?limit=120`),
        axios.get<FxData>(`${API_URL}/api/market-data/fx-rates`),
        axios.get<{ current_base_rates: Record<string, MarketRate> }>(`${API_URL}/api/market-data`),
      ]);
      if (!mountedRef.current) return;
      setHistory(hRes.data.history ?? []);
      setFx(fRes.data);
      setMetalRates(mRes.data.current_base_rates ?? {});
      setLastSync(Math.floor(Date.now() / 1000));
    } catch {
      // keep previous data on error
    } finally {
      if (mountedRef.current) { setLoading(false); setRefreshing(false); }
    }
  }, []);

  useEffect(() => {
    mountedRef.current = true;
    const run = async () => { await fetchAll(); };
    run();
    const iv = setInterval(run, 60000);
    return () => { mountedRef.current = false; clearInterval(iv); };
  }, [fetchAll]);

  const getMetalData = (key: string) =>
    history.filter((p) => p.metal === key && p.price_usd > 0).slice().reverse()
      .map((p) => ({ ...p, price_display: p.price_usd * rate, time: formatTime(p.timestamp) }));

  const currentUsd = (key: string, fallback?: number) => {
    const d = getMetalData(key).filter((p) => p.price_usd > 0);
    return d[d.length - 1]?.price_usd ?? fallback ?? 0;
  };
  const prevUsd = (key: string, fallback?: number) => {
    const d = getMetalData(key).filter((p) => p.price_usd > 0);
    return d[d.length - 2]?.price_usd ?? d[d.length - 1]?.price_usd ?? fallback ?? 0;
  };

  if (loading) {
    return (
      <div className="empty-state processing-state">
        <div className="spinner" />
        <h2>Synchronising Market Node</h2>
        <p>Fetching agentic discovery snapshots and live FX rates…</p>
      </div>
    );
  }

  return (
    <div className="market-page" style={{ position: 'relative' }}>
      <SparkleOverlay active={!loading} />

      {/* Header */}
      <header className="market-header">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 6 }}>
            <Link href="/" style={{ color: 'var(--primary)', display: 'flex', alignItems: 'center' }}>
              <ArrowLeft size={20} />
            </Link>
            <h1 style={{ margin: 0, fontSize: '1.6rem' }}>Market Intel Dashboard</h1>
            <Sparkles size={18} style={{ color: 'var(--accent)', opacity: 0.8 }} />
          </div>
          <p className="subtle">Live agentic metal snapshots · LME cross-check · 5-currency FX</p>
        </div>
        <div style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
          <div className="currency-tabs">
            {CURRENCIES.map((c) => (
              <button key={c} type="button" className={`currency-tab ${currency === c ? 'active' : ''}`} onClick={() => setCurrency(c)}>
                {SYM[c]} {c}
              </button>
            ))}
          </div>
          <button className="refresh-btn" type="button" onClick={() => fetchAll(true)} disabled={refreshing}>
            <RefreshCw size={14} className={refreshing ? 'spin-icon' : ''} />
            Refresh
          </button>
          {lastSync > 0 && (
            <div className="status-strip" style={{ whiteSpace: 'nowrap' }}>
              <Clock size={14} />
              <span>{formatTime(lastSync)} IST</span>
            </div>
          )}
        </div>
      </header>

      {/* FX Banner */}
      {fx && (
        <motion.div className="fx-banner" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
          <span className="eyebrow">Live FX · {fx.source} · {fx.as_of}</span>
          <div className="fx-rates">
            {Object.entries(fx.rates).map(([c, r]) => (
              <span
                key={c}
                className={`fx-pill ${currency === c ? 'fx-active' : ''}`}
                onClick={() => setCurrency(c as Cur)}
              >
                {SYM[c as Cur] ?? c}{Number(r).toFixed(c === 'USD' ? 1 : c === 'EUR' || c === 'GBP' ? 4 : 2)}
                <small>/{c}</small>
              </span>
            ))}
          </div>
        </motion.div>
      )}

      {/* Ticker row */}
      <div className="ticker-row">
        {metals.map((m, i) => (
          <motion.div key={m.key} initial={{ opacity: 0, y: 14 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
            <PriceTicker label={m.name} value={currentUsd(m.key, m.rate?.current_price) * rate} prev={prevUsd(m.key, m.rate?.current_price) * rate} sym={sym} />
          </motion.div>
        ))}
      </div>

      {/* Charts */}
      <div className="market-charts">
        {metals.map((m, idx) => {
          const data = getMetalData(m.key);
          const cur  = currentUsd(m.key, m.rate?.current_price) * rate;
          const prev = prevUsd(m.key, m.rate?.current_price) * rate;
          const up   = cur >= prev;
          const prices = data.map((d) => d.price_usd * rate);
          const minP = prices.length ? Math.min(...prices) * 0.998 : 0;
          const maxP = prices.length ? Math.max(...prices) * 1.002 : 10;

          return (
            <motion.div key={m.key} className="market-chart-card" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: idx * 0.1 }}>
              <div className="chart-card-header">
                <div>
                  <span className="eyebrow" style={{ color: m.color }}>{m.name}</span>
                  <div style={{ display: 'flex', alignItems: 'baseline', gap: 10, marginTop: 4 }}>
                    <AnimatePresence mode="wait">
                      <motion.strong
                        key={cur.toFixed(4)}
                        className="live-price-num"
                        initial={{ opacity: 0, y: up ? 8 : -8 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        style={{ color: m.color }}
                      >
                        {fmt(cur, sym)}<small style={{ fontSize: '0.9rem', color: 'var(--muted)', fontWeight: 400 }}>/kg</small>
                      </motion.strong>
                    </AnimatePresence>
                    <span className={`delta-pill ${up ? 'up' : 'down'}`}>
                      {up ? '▲' : '▼'} {fmt(Math.abs(cur - prev), sym)}
                    </span>
                  </div>
                </div>
                <div className="live-dot-wrapper">
                  <span className="live-dot" style={{ background: m.color }} />
                  <span style={{ color: 'var(--muted)', fontSize: '0.75rem' }}>{m.rate?.is_live ? 'Live' : 'Reference'}</span>
                </div>
              </div>

              <div style={{ width: '100%', height: 240 }}>
                {data.length > 1 ? (
                  <ReactECharts
                    style={{ height: 240, width: '100%' }}
                    option={{
                      backgroundColor: 'transparent',
                      grid: { top: 12, right: 8, bottom: 28, left: 64 },
                      tooltip: {
                        trigger: 'axis',
                        backgroundColor: 'rgba(15,23,42,0.92)',
                        borderColor: m.color,
                        borderWidth: 1,
                        textStyle: { color: '#f8fafc', fontSize: 12 },
                        formatter: (params: { name: string; value: number }[]) => {
                          const p = params[0];
                          return `<b style="color:${m.color}">${p.name} IST</b><br/>${sym}${p.value.toFixed(2)} / kg`;
                        },
                      },
                      xAxis: {
                        type: 'category',
                        data: data.map((d) => d.time),
                        axisLine: { show: false },
                        axisTick: { show: false },
                        axisLabel: { color: '#64748b', fontSize: 10, interval: 'auto' },
                        splitLine: { show: false },
                      },
                      yAxis: {
                        type: 'value',
                        min: minP,
                        max: maxP,
                        axisLine: { show: false },
                        axisTick: { show: false },
                        axisLabel: { color: '#64748b', fontSize: 10, formatter: (v: number) => `${sym}${v.toFixed(1)}` },
                        splitLine: { lineStyle: { color: 'rgba(148,163,184,0.1)' } },
                      },
                      series: [{
                        type: 'line',
                        data: data.map((d) => d.price_display),
                        smooth: true,
                        symbol: 'none',
                        lineStyle: { color: m.color, width: 2.5 },
                        areaStyle: {
                          color: { type: 'linear', x: 0, y: 0, x2: 0, y2: 1,
                            colorStops: [
                              { offset: 0, color: m.gradA + 'aa' },
                              { offset: 1, color: m.gradB + '00' },
                            ],
                          },
                        },
                        markLine: {
                          silent: true,
                          data: [{ yAxis: prev }],
                          lineStyle: { color: m.color, type: 'dashed', opacity: 0.45 },
                          label: { show: false },
                          symbol: ['none', 'none'],
                        },
                      }],
                    }}
                    notMerge
                    lazyUpdate
                  />
                ) : (
                  <div className="chart-empty">
                    <TrendingUp size={28} style={{ color: m.color, opacity: 0.45 }} />
                    <p>Accumulating data points for trend visualisation…</p>
                  </div>
                )}
              </div>

              {data.length > 3 && (
                <div style={{ marginTop: 8 }}>
                  <p style={{ margin: '0 0 4px', fontSize: '0.72rem', color: 'var(--muted)', fontWeight: 700, textTransform: 'uppercase' }}>
                    24-pt D3 trend
                  </p>
                  <D3Sparkline data={data.slice(-24).map((d) => d.price_display)} color={m.color} width={320} height={44} />
                </div>
              )}
            </motion.div>
          );
        })}
      </div>

      <footer className="market-footer" style={{ marginTop: 32 }}>
        <Activity size={16} />
        <span>{history.length} discovery snapshots · Agentic LME web search · FX via {fx?.source ?? 'Frankfurter'}</span>
      </footer>
    </div>
  );
}
