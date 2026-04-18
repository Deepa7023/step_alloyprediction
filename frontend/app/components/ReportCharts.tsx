'use client';

import React, { useMemo } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { scaleSequential } from 'd3-scale';
import { interpolateRgbBasis } from 'd3-interpolate';
import type { AgentReport } from '../types/report';

const palette = ['#2f6f4e', '#b15f2a', '#657069', '#8b5f3c'];

export default function ReportCharts({ report }: { report: AgentReport }) {
  const cost = report.cost_estimation;
  const market = report.market_snapshot;

  const costData = useMemo(
    () => [
      { name: 'Material', value: cost.material_cost },
      { name: 'Machine', value: cost.machine_cost },
      { name: 'Die amort.', value: cost.amortization },
      { name: 'Port', value: cost.port_cost },
    ],
    [cost.amortization, cost.machine_cost, cost.material_cost, cost.port_cost],
  );

  const locationData = useMemo(
    () =>
      (market.location_price_table || []).map((row) => ({
        name: row.city,
        fullName: row.name,
        price: row.location_adjusted_usd_per_kg,
        status: row.is_live_price ? 'Live' : 'Reference',
        premium: row.regional_premium_percent || 0,
      })),
    [market.location_price_table],
  );

  const colorScale = scaleSequential(interpolateRgbBasis(['#2f6f4e', '#b15f2a'])).domain([0, Math.max(locationData.length - 1, 1)]);

  return (
    <div className="chart-grid">
      <div className="chart-card">
        <div className="chart-heading">
          <span>Per-part cost mix</span>
          <strong>${cost.per_part_cost ?? cost.total_unit_cost}</strong>
        </div>
        <ResponsiveContainer width="100%" height={260}>
          <PieChart>
            <Pie data={costData} dataKey="value" nameKey="name" innerRadius={58} outerRadius={88} paddingAngle={3}>
              {costData.map((entry, index) => (
                <Cell key={entry.name} fill={palette[index % palette.length]} />
              ))}
            </Pie>
            <Tooltip formatter={(value) => [`$${Number(value || 0).toFixed(2)}`, 'Cost']} />
          </PieChart>
        </ResponsiveContainer>
        <div className="chart-legend">
          {costData.map((item, index) => (
            <span key={item.name}>
              <i style={{ background: palette[index % palette.length] }} />
              {item.name}
            </span>
          ))}
        </div>
      </div>

      <div className="chart-card">
        <div className="chart-heading">
          <span>Location landed metal price</span>
          <strong>{market.is_live_metal_price ? 'Live feed' : 'Reference basis'}</strong>
        </div>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={locationData} margin={{ top: 14, right: 8, left: 0, bottom: 34 }}>
            <CartesianGrid stroke="#e6ebe4" vertical={false} />
            <XAxis dataKey="name" angle={-24} textAnchor="end" height={64} tick={{ fill: '#657069', fontSize: 12 }} />
            <YAxis tick={{ fill: '#657069', fontSize: 12 }} width={44} />
            <Tooltip
              formatter={(value) => [`$${Number(value || 0).toFixed(4)}/kg`, 'Landed price']}
              labelFormatter={(_, payload) => payload?.[0]?.payload?.fullName || ''}
            />
            <Bar dataKey="price" radius={[6, 6, 0, 0]}>
              {locationData.map((entry, index) => (
                <Cell key={entry.fullName} fill={colorScale(index)} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
        <p className="chart-note">
          {market.is_live_metal_price
            ? 'Bars use live metal feed plus regional premium and freight.'
            : 'Bars use reference alloy price because the live alloy feed is unavailable for this API plan.'}
        </p>
      </div>
    </div>
  );
}
