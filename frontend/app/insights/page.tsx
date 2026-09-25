'use client';

import { useEffect, useState } from 'react';
import { ArrowUpRight, Lightbulb } from 'lucide-react';
import DashboardShell from '@/components/dashboard-shell';
import { apiFetch } from '@/lib/api';
import { Badge, ErrorState, LoadingState, Panel, formatDate } from '@/components/ui';

type Insight = Record<string, any>;

export default function InsightsPage() {
  const [data, setData] = useState<Insight[] | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { apiFetch<{ insights: Insight[] }>('/api/insights').then((payload) => setData(payload.insights)).catch((reason) => setError(reason.message)); }, []);
  if (error) return <DashboardShell title="Business Insights"><ErrorState message={error} /></DashboardShell>;
  if (!data) return <DashboardShell title="Business Insights"><LoadingState /></DashboardShell>;
  return <DashboardShell title="Business Insights" subtitle="Automatically calculated findings from the synthetic transaction period. Each card includes a comparison and business implication.">
    <div className="mb-5 rounded-lg border border-blue-400/20 bg-blue-400/5 p-3 text-xs leading-5 text-blue-100/80"><Lightbulb size={15} className="mr-2 inline text-blue-300" />These are analytical recommendations for portfolio demonstration, not final business decisions.</div>
    <div className="grid gap-4 md:grid-cols-2">{data.map((insight) => <Panel key={String(insight.insight_id)} title={String(insight.title)} eyebrow={String(insight.insight_id)} action={<Badge tone="blue">Calculated</Badge>}><p className="text-xl font-semibold text-white">{String(insight.metric)}</p><p className="mt-2 text-xs text-slate-400">Comparison: {String(insight.comparison)}</p><p className="mt-4 text-sm leading-6 text-slate-300">{String(insight.explanation)}</p><div className="mt-4 flex gap-2 rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-xs leading-5 text-amber-100/80"><ArrowUpRight size={14} className="mt-0.5 shrink-0" />{String(insight.business_implication)}</div><p className="mt-4 text-[10px] text-slate-600">Data period: {formatDate(insight.period_start)} — {formatDate(insight.period_end)}</p></Panel>)}</div>
  </DashboardShell>;
}
