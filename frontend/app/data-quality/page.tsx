'use client';

import { useEffect, useState } from 'react';
import { CheckCircle2, Database, XCircle } from 'lucide-react';
import DashboardShell from '@/components/dashboard-shell';
import { apiFetch } from '@/lib/api';
import { Badge, ErrorState, LoadingState, MetricCard, Panel, formatNumber } from '@/components/ui';

type Quality = { quality_score: number; checks_passed: number; checks_failed: number; row_counts: Record<string, number>; composition: Record<string, any>; issues: Record<string, any>[]; data_freshness: Record<string, any> };

export default function DataQualityPage() {
  const [data, setData] = useState<Quality | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { apiFetch<Quality>('/api/data-quality').then(setData).catch((reason) => setError(reason.message)); }, []);
  if (error) return <DashboardShell title="Data Quality"><ErrorState message={error} /></DashboardShell>;
  if (!data) return <DashboardShell title="Data Quality"><LoadingState /></DashboardShell>;
  const checks = (data as any).checks || [];
  return <DashboardShell title="Data Quality" subtitle="Schema, integrity, validity and freshness checks generated from the current synthetic dataset.">
    <div className="grid gap-3 sm:grid-cols-3"><MetricCard label="Quality score" value={`${formatNumber(data.quality_score)}/100`} detail="100 minus documented severity penalties" tone={data.quality_score >= 90 ? 'green' : 'amber'} icon={<Database size={16} />} /><MetricCard label="Checks passed" value={formatNumber(data.checks_passed)} tone="green" icon={<CheckCircle2 size={16} />} /><MetricCard label="Checks failed" value={formatNumber(data.checks_failed)} tone={data.checks_failed ? 'red' : 'blue'} icon={<XCircle size={16} />} /></div>
    <div className="mt-4 grid gap-4 xl:grid-cols-[1fr_0.7fr]"><Panel title="Quality checks" eyebrow="Calculated controls"><div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-xs"><thead className="border-b border-line text-[10px] uppercase text-slate-500"><tr><th className="py-3">Check</th><th className="py-3">Table</th><th className="py-3">Severity</th><th className="py-3">Observed</th><th className="py-3">Status</th><th className="py-3">Details</th></tr></thead><tbody>{checks.map((check: any) => <tr key={String(check.check_id)} className="border-b border-line/60"><td className="py-3 text-white">{String(check.check_name)}</td><td className="py-3 text-slate-400">{String(check.table_name)}</td><td className="py-3"><Badge tone={String(check.severity)}>{String(check.severity)}</Badge></td><td className="py-3 text-slate-300">{formatNumber(check.observed_value, 3)}</td><td className="py-3"><Badge tone={String(check.status)}>{String(check.status)}</Badge></td><td className="max-w-[360px] py-3 text-slate-500">{String(check.details)}</td></tr>)}</tbody></table></div></Panel><Panel title="Score composition" eyebrow="Quality methodology"><div className="space-y-4 text-xs"><div className="flex justify-between"><span className="text-slate-500">Base score</span><span className="text-white">{formatNumber(data.composition?.base_score)}</span></div><div className="flex justify-between"><span className="text-slate-500">Applied penalty</span><span className="text-red-200">-{formatNumber(data.composition?.applied_penalty)}</span></div><div className="rounded-lg border border-line bg-slate-900/50 p-3 leading-5 text-slate-400">Critical: -20 · High: -10 · Medium: -5 · Low: -2 per failed check.</div><div><p className="text-slate-500">Latest event</p><p className="mt-1 text-slate-200">{String(data.data_freshness?.latest_event)}</p><p className="mt-1 text-slate-500">Period coverage: {formatNumber(data.data_freshness?.event_period_days)} days</p></div></div></Panel></div>
    <Panel className="mt-4" title="Row counts" eyebrow="Loaded entities"><div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">{Object.entries(data.row_counts || {}).map(([table, count]) => <div key={table} className="rounded-lg border border-line bg-slate-900/40 p-3"><p className="text-[10px] uppercase text-slate-500">{table}</p><p className="mt-1 text-lg font-semibold text-white">{formatNumber(count)}</p></div>)}</div></Panel>
  </DashboardShell>;
}
