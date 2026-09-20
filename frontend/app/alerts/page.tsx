'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Download, ExternalLink, Search, UserRound } from 'lucide-react';
import DashboardShell from '@/components/dashboard-shell';
import { apiFetch, queryString } from '@/lib/api';
import type { Alert, Paginated } from '@/lib/types';
import { Badge, Button, EmptyState, ErrorState, LoadingState, Panel, Select, formatDate, formatMoney, formatNumber } from '@/components/ui';

const statuses = ['New', 'In Review', 'Escalated', 'Confirmed Fraud', 'False Positive', 'Closed'];

export default function AlertsPage() {
  const [data, setData] = useState<Paginated<Alert> | null>(null);
  const [search, setSearch] = useState('');
  const [status, setStatus] = useState('');
  const [priority, setPriority] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');

  const load = () => apiFetch<Paginated<Alert>>(`/api/alerts${queryString({ page, page_size: 20, search, alert_status: status, priority })}`).then(setData).catch((reason) => setError(reason.message));
  useEffect(() => { load(); }, [page, status, priority]);

  async function updateStatus(alertId: string, alertStatus: string) {
    await apiFetch(`/api/alerts/${alertId}`, { method: 'PATCH', body: JSON.stringify({ alert_status: alertStatus }) });
    load();
  }

  return <DashboardShell title="Alert Queue" subtitle="Prioritized alerts for human review. Sort and filter the queue by score, workflow status and operational priority." actions={<a href="/api/export/alerts" className="inline-flex items-center gap-2 rounded-md border border-line bg-slate-800/70 px-3 py-2 text-xs text-slate-200 hover:border-blue-400/40"><Download size={14} />Export CSV</a>}>
    <Panel title="Queue controls" eyebrow="Triage workspace">
      <div className="flex flex-wrap gap-3"><div className="relative min-w-[240px] flex-1"><Search size={15} className="absolute left-3 top-2.5 text-slate-500" /><input value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && (setPage(1), load())} placeholder="Search alert, customer or transaction ID" className="w-full rounded-md border border-line bg-slate-900 py-2 pl-9 pr-3 text-xs text-slate-200 outline-none focus:border-blue-400/50" /></div><Select value={status} onChange={(value) => { setStatus(value); setPage(1); }}><option value="">All statuses</option>{statuses.map((item) => <option key={item}>{item}</option>)}</Select><Select value={priority} onChange={(value) => { setPriority(value); setPage(1); }}><option value="">All priorities</option><option>P1</option><option>P2</option><option>P3</option><option>P4</option></Select><Button onClick={() => { setPage(1); load(); }}>Apply filters</Button></div>
    </Panel>
    <Panel className="mt-4" title="Investigation queue" eyebrow={`${formatNumber(data?.pagination.total || 0)} matching alerts`}>
      {error ? <ErrorState message={error} /> : !data ? <LoadingState /> : data.items.length === 0 ? <EmptyState /> : <div className="overflow-x-auto"><table className="w-full min-w-[1050px] text-left text-xs"><thead className="border-b border-line text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-3">Alert</th><th className="px-3 py-3">Created</th><th className="px-3 py-3">Customer</th><th className="px-3 py-3">Amount</th><th className="px-3 py-3">Score</th><th className="px-3 py-3">Rules</th><th className="px-3 py-3">SLA age</th><th className="px-3 py-3">Status</th><th className="px-3 py-3">Action</th></tr></thead><tbody>{data.items.map((alert) => <tr key={alert.alert_id} className="border-b border-line/70 hover:bg-slate-800/30"><td className="px-3 py-3"><Link href={`/alerts/${alert.alert_id}`} className="font-semibold text-blue-300 hover:text-blue-100">{alert.alert_id}</Link><p className="mt-1 text-[10px] text-slate-500">{String(alert.transaction_id)}</p></td><td className="px-3 py-3 text-slate-400">{formatDate(alert.created_at)}</td><td className="px-3 py-3"><Link href={`/customers/${alert.customer_id}`} className="text-slate-200 hover:text-blue-200">{alert.customer_id}</Link><p className="mt-1 text-[10px] text-slate-500">{String(alert.anonymized_name || 'Anonymous customer')}</p></td><td className="px-3 py-3 font-medium text-white">{formatMoney(alert.amount, String(alert.currency || 'USD'))}</td><td className="px-3 py-3"><Badge tone={String(alert.risk_level)}>{formatNumber(alert.risk_score, 1)} · {String(alert.risk_level)}</Badge></td><td className="max-w-[180px] px-3 py-3 text-slate-400">{Array.isArray(alert.triggered_rules) ? (alert.triggered_rules as unknown[]).join(', ') : String(alert.triggered_rules || '—')}</td><td className="px-3 py-3 text-slate-400">{formatNumber(alert.sla_age_hours, 1)}h</td><td className="px-3 py-3"><Select value={String(alert.alert_status)} onChange={(value) => updateStatus(alert.alert_id, value)}><option>{String(alert.alert_status)}</option>{statuses.filter((item) => item !== alert.alert_status).map((item) => <option key={item}>{item}</option>)}</Select></td><td className="px-3 py-3"><Link href={`/alerts/${alert.alert_id}`} className="inline-flex items-center gap-1 text-blue-300 hover:text-blue-100"><ExternalLink size={13} />Open</Link></td></tr>)}</tbody></table></div>}
      {data && data.pagination.pages > 1 && <div className="mt-4 flex items-center justify-between border-t border-line pt-4 text-xs text-slate-400"><span>Page {data.pagination.page} of {data.pagination.pages}</span><div className="flex gap-2"><Button disabled={page <= 1} onClick={() => setPage((value) => Math.max(1, value - 1))}>Previous</Button><Button disabled={page >= data.pagination.pages} onClick={() => setPage((value) => value + 1)}>Next</Button></div></div>}
    </Panel>
    <div className="mt-4 flex items-center gap-2 text-xs text-slate-500"><UserRound size={14} />Assignment and workflow status changes are stored through the API; final decisions should be supported by investigator evidence.</div>
  </DashboardShell>;
}
