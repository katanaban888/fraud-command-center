'use client';

import { useEffect, useState } from 'react';
import { BrainCircuit, Info, Split } from 'lucide-react';
import DashboardShell from '@/components/dashboard-shell';
import { apiFetch } from '@/lib/api';
import type { ModelReport } from '@/lib/types';
import { Badge, ErrorState, LoadingState, MetricCard, Panel, formatMoney, formatNumber } from '@/components/ui';
import { BarMetricChart } from '@/components/charts';

export default function ModelsPage() {
  const [data, setData] = useState<ModelReport | null>(null);
  const [error, setError] = useState('');
  useEffect(() => { apiFetch<ModelReport>('/api/model/metrics').then(setData).catch((reason) => setError(reason.message)); }, []);
  if (error) return <DashboardShell title="Model Evaluation"><ErrorState message={error} /></DashboardShell>;
  if (!data) return <DashboardShell title="Model Evaluation"><LoadingState /></DashboardShell>;
  const distribution = data.class_distribution || {};
  const combined = data.metrics?.['rules + combined score'] || {};
  const importance = (data.feature_importance || []).map((row) => ({ feature: String(row.feature).slice(0, 24), importance: Number(row.absolute_importance || 0) })).slice(0, 10);
  return <DashboardShell title="Model Evaluation" subtitle="Time-based evaluation of rules, anomaly detection and interpretable Logistic Regression. ML prioritizes alerts; it does not replace human review.">
    <div className="mb-5 rounded-lg border border-blue-400/20 bg-blue-400/5 p-3 text-xs leading-5 text-blue-100/80"><Info size={15} className="mr-2 inline text-blue-300" />Accuracy is not the primary metric when fraud is rare. Precision, recall, F1 and PR-AUC better describe the investigation trade-off.</div>
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5"><MetricCard label="Normal rows" value={formatNumber(distribution.normal)} icon={<Split size={16} />} /><MetricCard label="Fraud rows" value={formatNumber(distribution.fraud)} detail={`${formatNumber(Number(distribution.fraud_rate) * 100, 2)}% synthetic rate`} tone="red" /><MetricCard label="Combined precision" value={`${formatNumber(Number(combined.precision) * 100, 1)}%`} tone="green" /><MetricCard label="Combined recall" value={`${formatNumber(Number(combined.recall) * 100, 1)}%`} /><MetricCard label="Combined PR-AUC" value={formatNumber(Number(combined.pr_auc), 3)} tone="blue" /></div>
    <Panel className="mt-4" title="Approach comparison" eyebrow="Rules versus ML prioritization"><div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-xs"><thead className="border-b border-line text-[10px] uppercase text-slate-500"><tr><th className="py-3">Approach</th><th className="py-3">Threshold</th><th className="py-3">Precision</th><th className="py-3">Recall</th><th className="py-3">F1</th><th className="py-3">ROC-AUC</th><th className="py-3">PR-AUC</th><th className="py-3">Alert volume</th><th className="py-3">Workload</th></tr></thead><tbody>{Object.entries(data.metrics || {}).map(([name, metric]) => <tr key={name} className="border-b border-line/70"><td className="py-3 font-semibold text-white">{name}</td><td className="py-3 text-slate-400">{formatNumber(metric.threshold, 1)}</td><td className="py-3">{formatNumber(Number(metric.precision) * 100, 1)}%</td><td className="py-3">{formatNumber(Number(metric.recall) * 100, 1)}%</td><td className="py-3">{formatNumber(Number(metric.f1), 3)}</td><td className="py-3">{formatNumber(Number(metric.roc_auc), 3)}</td><td className="py-3 text-blue-200">{formatNumber(Number(metric.pr_auc), 3)}</td><td className="py-3">{formatNumber(metric.alert_volume)}</td><td className="py-3 text-amber-200">{formatNumber(metric.investigation_workload_minutes)} min</td></tr>)}</tbody></table></div></Panel>
    <div className="mt-4 grid gap-4 xl:grid-cols-2"><Panel title="Logistic coefficient importance" eyebrow="Absolute coefficient magnitude"><BarMetricChart data={importance} nameKey="feature" dataKey="importance" color="#a78bfa" /></Panel><Panel title="Threshold analysis" eyebrow="Combined-score what-if"><div className="overflow-x-auto"><table className="w-full text-left text-xs"><thead className="border-b border-line text-[10px] uppercase text-slate-500"><tr><th className="py-2">Threshold</th><th className="py-2">Precision</th><th className="py-2">Recall</th><th className="py-2">Alerts</th><th className="py-2">FPR</th></tr></thead><tbody>{(data.threshold_analysis || []).map((row) => <tr key={String(row.threshold)} className="border-b border-line/60"><td className="py-2 text-white">{String(row.threshold)}</td><td className="py-2">{formatNumber(Number(row.precision) * 100, 1)}%</td><td className="py-2">{formatNumber(Number(row.recall) * 100, 1)}%</td><td className="py-2">{formatNumber(row.alert_volume)}</td><td className="py-2 text-red-200">{formatNumber(Number(row.false_positive_rate) * 100, 1)}%</td></tr>)}</tbody></table></div></Panel></div>
    <Panel className="mt-4" title="Model limitations" eyebrow="Read before interpreting results"><ul className="grid gap-2 md:grid-cols-2">{(data.model_limitations || []).map((limitation) => <li key={limitation} className="flex gap-2 text-xs leading-5 text-slate-400"><BrainCircuit size={14} className="mt-0.5 shrink-0 text-blue-300" />{limitation}</li>)}</ul></Panel>
  </DashboardShell>;
}
