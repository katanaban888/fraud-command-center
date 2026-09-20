'use client';

import { useEffect, useState } from 'react';
import { AlertTriangle, BarChart3, CircleDollarSign, FileWarning, ShieldCheck, Timer, TrendingUp } from 'lucide-react';
import DashboardShell from '@/components/dashboard-shell';
import { BarMetricChart, DonutChart, TrendChart } from '@/components/charts';
import { apiFetch, queryString } from '@/lib/api';
import type { OverviewResponse } from '@/lib/types';
import { ErrorState, LoadingState, MetricCard, Panel, Select, formatMoney, formatNumber } from '@/components/ui';

export default function OverviewPage() {
  const [data, setData] = useState<OverviewResponse | null>(null);
  const [error, setError] = useState('');
  const [channel, setChannel] = useState('');
  const [riskLevel, setRiskLevel] = useState('');
  const [segment, setSegment] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  useEffect(() => {
    const params = queryString({ channel, risk_level: riskLevel, segment, date_from: dateFrom, date_to: dateTo });
    apiFetch<OverviewResponse>(`/api/overview${params}`).then(setData).catch((reason) => setError(reason.message));
  }, [channel, riskLevel, segment, dateFrom, dateTo]);

  const kpi = data?.kpis || {};
  const series = data?.series || {};
  const volume = series.volume_over_time || [];
  const rules = series.top_triggered_rules || [];
  const risks = series.alerts_by_risk_level || [];
  const channels = series.alerts_by_channel || [];
  const regions = series.suspicious_amount_by_region || [];
  if (error) return <DashboardShell title="Overview" subtitle="Explainable monitoring overview"><ErrorState message={error} /></DashboardShell>;
  if (!data) return <DashboardShell title="Overview" subtitle="Explainable monitoring overview"><LoadingState /></DashboardShell>;

  return <DashboardShell title="Overview" subtitle="A calculated view of transaction activity, synthetic fraud labels, risk queue volume and analyst workload.">
    <div className="mb-5 flex flex-wrap items-center gap-2 rounded-lg border border-blue-400/20 bg-blue-400/5 p-3 text-xs text-blue-100/80"><ShieldCheck size={15} className="text-blue-300" />Dashboard data is based on synthetic transactions generated for portfolio demonstration.</div>
    <div className="mb-6 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
      <MetricCard label="Total transactions" value={formatNumber(kpi.total_transactions)} detail="Rows in the selected period" icon={<BarChart3 size={16} />} />
      <MetricCard label="Transaction volume" value={formatMoney(kpi.total_transaction_volume)} detail="Synthetic transaction amount" icon={<CircleDollarSign size={16} />} tone="blue" />
      <MetricCard label="Open alerts" value={formatNumber(kpi.open_alerts)} detail={`${formatNumber(kpi.suspicious_transactions)} prioritized alerts`} icon={<FileWarning size={16} />} tone="amber" />
      <MetricCard label="Critical alerts" value={formatNumber(kpi.critical_alerts)} detail="Highest score band" icon={<AlertTriangle size={16} />} tone="red" />
      <MetricCard label="False-positive proxy" value={`${formatNumber(kpi.false_positive_rate, 1)}%`} detail="Synthetic label evaluation, not disposition" icon={<TrendingUp size={16} />} tone="green" />
    </div>
    <div className="mb-6 grid gap-3 rounded-xl border border-line bg-[#0a1727] p-4 md:grid-cols-5">
      <label className="text-xs text-slate-400">Date from<input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} className="mt-1 w-full rounded-md border border-line bg-slate-900 px-2 py-2 text-xs text-slate-200" /></label>
      <label className="text-xs text-slate-400">Date to<input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} className="mt-1 w-full rounded-md border border-line bg-slate-900 px-2 py-2 text-xs text-slate-200" /></label>
      <label className="text-xs text-slate-400">Channel<Select value={channel} onChange={setChannel} className="mt-1 w-full"><option value="">All channels</option><option>Mobile App</option><option>Web</option><option>Card</option><option>API</option><option>ATM</option></Select></label>
      <label className="text-xs text-slate-400">Risk level<Select value={riskLevel} onChange={setRiskLevel} className="mt-1 w-full"><option value="">All levels</option><option>Low</option><option>Medium</option><option>High</option><option>Critical</option></Select></label>
      <label className="text-xs text-slate-400">Customer segment<Select value={segment} onChange={setSegment} className="mt-1 w-full"><option value="">All segments</option><option>standard_customer</option><option>high_value_customer</option><option>small_business</option><option>new_customer</option><option>high_risk_customer</option></Select></label>
    </div>
    <div className="grid gap-4 xl:grid-cols-2">
      <Panel title="Transaction and alert trend" eyebrow="Time series"><TrendChart data={volume} dataKey="transaction_count" secondaryKey="alerts" /></Panel>
      <Panel title="Fraud rate over time" eyebrow="Synthetic ground truth"><TrendChart data={volume} dataKey="fraud_rate" color="#f59e0b" /></Panel>
      <Panel title="Alerts by risk level" eyebrow="Prioritized queue"><DonutChart data={risks} nameKey="risk_level" dataKey="alerts" /></Panel>
      <Panel title="Alerts by channel" eyebrow="Operational context"><BarMetricChart data={channels} nameKey="channel" dataKey="alerts" color="#34d399" /></Panel>
      <Panel title="Top triggered rules" eyebrow="Rule engine signal"><BarMetricChart data={rules} nameKey="rule_id" dataKey="triggered" color="#a78bfa" /></Panel>
      <Panel title="Suspicious amount by region" eyebrow="Synthetic fraud-labelled amount"><BarMetricChart data={regions} nameKey="region" dataKey="suspicious_amount" color="#f97316" /></Panel>
    </div>
    <div className="mt-4 grid gap-4 xl:grid-cols-2">
      <Panel title="Selected-period summary" eyebrow="Risk operations"><div className="grid gap-4 sm:grid-cols-3"><div><p className="text-xs text-slate-500">Suspicious amount</p><p className="mt-1 text-xl font-semibold text-white">{formatMoney(kpi.suspicious_amount)}</p></div><div><p className="text-xs text-slate-500">Confirmed fraud proxy</p><p className="mt-1 text-xl font-semibold text-white">{formatNumber(kpi.confirmed_fraud)}</p></div><div><p className="text-xs text-slate-500">Prevented-loss estimate</p><p className="mt-1 text-xl font-semibold text-emerald-200">{formatMoney(kpi.estimated_prevented_loss)}</p></div></div><p className="mt-4 text-xs leading-5 text-slate-500">Estimated prevented loss applies the documented synthetic prevention-rate assumption. It is not a measured bank outcome.</p></Panel>
      <Panel title="Analyst workload" eyebrow="Estimated minutes"><div className="flex items-center gap-4"><Timer className="text-amber-300" size={28} /><div><p className="text-2xl font-semibold text-white">{formatNumber((series.analyst_workload_over_time || []).reduce((sum, row) => sum + Number(row.analyst_minutes || 0), 0))}</p><p className="text-xs text-slate-500">estimated analyst minutes in the selected period</p></div></div></Panel>
    </div>
  </DashboardShell>;
}
