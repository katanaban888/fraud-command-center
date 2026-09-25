'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ClipboardList, RefreshCcw } from 'lucide-react';
import DashboardShell from '@/components/dashboard-shell';
import { apiFetch } from '@/lib/api';
import type { Paginated } from '@/lib/types';
import { Badge, Button, EmptyState, ErrorState, LoadingState, MetricCard, Panel, Select, formatDate, formatMoney, formatNumber } from '@/components/ui';

type CaseRecord = Record<string, any> & { case_id: string; case_status: string; priority: string; alert_id: string };
type CaseAnalytics = { average_resolution_hours: number; cases_per_analyst: Record<string, any>[]; confirmed_fraud_rate: number; false_positive_rate: number; open_cases_by_priority: Record<string, any>[]; overdue_investigations: number };

export default function InvestigationsPage() {
  const [data, setData] = useState<Paginated<CaseRecord> | null>(null);
  const [analytics, setAnalytics] = useState<CaseAnalytics | null>(null);
  const [status, setStatus] = useState('');
  const [error, setError] = useState('');
  const load = () => apiFetch<Paginated<CaseRecord>>(`/api/cases?page_size=100${status ? `&status=${encodeURIComponent(status)}` : ''}`).then(setData).catch((reason) => setError(reason.message));
  useEffect(() => { load(); apiFetch<CaseAnalytics>('/api/cases/analytics').then(setAnalytics).catch(() => undefined); }, [status]);
  const items = data?.items || [];
  return <DashboardShell title="Investigations" subtitle="Case management for analyst notes, assignments, decisions, losses and resolution time. Cases are created from alert detail pages.">
    <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-5"><MetricCard label="Open cases" value={formatNumber(items.filter((item) => ['Open', 'In Progress', 'Escalated'].includes(item.case_status)).length)} icon={<ClipboardList size={16} />} /><MetricCard label="Average resolution" value={`${formatNumber(analytics?.average_resolution_hours || 0, 1)}h`} tone="blue" /><MetricCard label="Confirmed fraud rate" value={`${formatNumber(Number(analytics?.confirmed_fraud_rate || 0) * 100, 1)}%`} tone="red" /><MetricCard label="False-positive rate" value={`${formatNumber(Number(analytics?.false_positive_rate || 0) * 100, 1)}%`} tone="amber" /><MetricCard label="Overdue" value={formatNumber(analytics?.overdue_investigations || 0)} tone="red" /></div>
    <Panel className="mt-4" title="Investigation cases" eyebrow="Workflow queue" action={<Button variant="ghost" onClick={load}><RefreshCcw size={14} />Refresh</Button>}><div className="mb-4"><Select value={status} onChange={setStatus}><option value="">All statuses</option><option>Open</option><option>In Progress</option><option>Escalated</option><option>Resolved</option><option>Closed</option></Select></div>{error ? <ErrorState message={error} /> : !data ? <LoadingState /> : items.length === 0 ? <EmptyState message="No cases yet. Create a case from an alert detail page." /> : <div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-xs"><thead className="border-b border-line text-[10px] uppercase text-slate-500"><tr><th className="py-3">Case</th><th className="py-3">Alert</th><th className="py-3">Customer</th><th className="py-3">Priority</th><th className="py-3">Status</th><th className="py-3">Decision</th><th className="py-3">Opened</th><th className="py-3">Loss</th></tr></thead><tbody>{items.map((item) => <tr key={item.case_id} className="border-b border-line/60"><td className="py-3 font-semibold text-white">{item.case_id}</td><td className="py-3"><Link href={`/alerts/${item.alert_id}`} className="text-blue-300">{item.alert_id}</Link></td><td className="py-3 text-slate-400">{String(item.customer_id)}</td><td className="py-3"><Badge tone={String(item.priority)}>{String(item.priority)}</Badge></td><td className="py-3"><Badge tone={String(item.case_status)}>{String(item.case_status)}</Badge></td><td className="py-3 text-slate-400">{String(item.final_decision || 'Pending')}</td><td className="py-3 text-slate-500">{formatDate(item.opened_at)}</td><td className="py-3 text-slate-300">{item.estimated_loss ? formatMoney(item.estimated_loss) : '—'}</td></tr>)}</tbody></table></div>}</Panel>
  </DashboardShell>;
}
