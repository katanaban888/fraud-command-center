'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Download, Search } from 'lucide-react';
import DashboardShell from '@/components/dashboard-shell';
import { apiFetch, queryString } from '@/lib/api';
import type { Paginated, Transaction } from '@/lib/types';
import { Badge, Button, EmptyState, ErrorState, LoadingState, Panel, Select, formatDate, formatMoney, formatNumber } from '@/components/ui';

export default function TransactionsPage() {
  const [data, setData] = useState<Paginated<Transaction> | null>(null);
  const [search, setSearch] = useState('');
  const [channel, setChannel] = useState('');
  const [fraud, setFraud] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  const load = () => apiFetch<Paginated<Transaction>>(`/api/transactions${queryString({ page, page_size: 25, search, channel, is_fraud: fraud || undefined, sort_by: 'timestamp', sort_order: 'desc' })}`).then(setData).catch((reason) => setError(reason.message));
  useEffect(() => { load(); }, [page, channel, fraud]);
  return <DashboardShell title="Transaction Explorer" subtitle="Search the synthetic transaction fact table and move from an event to its rules, features, alerts and related entities." actions={<a href="/api/export/alerts" className="inline-flex items-center gap-2 rounded-md border border-line bg-slate-800/70 px-3 py-2 text-xs text-slate-200"><Download size={14} />Alert CSV</a>}>
    <Panel title="Transaction filters" eyebrow="Exploration"><div className="flex flex-wrap gap-3"><div className="relative min-w-[260px] flex-1"><Search size={15} className="absolute left-3 top-2.5 text-slate-500" /><input value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && (setPage(1), load())} placeholder="Search transaction, customer, account or beneficiary" className="w-full rounded-md border border-line bg-slate-900 py-2 pl-9 pr-3 text-xs text-slate-200 outline-none" /></div><Select value={channel} onChange={(value) => { setChannel(value); setPage(1); }}><option value="">All channels</option><option>Mobile App</option><option>Web</option><option>Card</option><option>API</option><option>ATM</option></Select><Select value={fraud} onChange={(value) => { setFraud(value); setPage(1); }}><option value="">All labels</option><option value="true">Synthetic fraud</option><option value="false">Normal label</option></Select><Button onClick={() => { setPage(1); load(); }}>Apply filters</Button></div></Panel>
    <Panel className="mt-4" title="Transactions" eyebrow={`${formatNumber(data?.pagination.total || 0)} matching rows`}>
      {error ? <ErrorState message={error} /> : !data ? <LoadingState /> : data.items.length === 0 ? <EmptyState /> : <div className="overflow-x-auto"><table className="w-full min-w-[1050px] text-left text-xs"><thead className="border-b border-line text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-3">Transaction</th><th className="px-3 py-3">Timestamp</th><th className="px-3 py-3">Customer</th><th className="px-3 py-3">Amount</th><th className="px-3 py-3">Channel</th><th className="px-3 py-3">Location</th><th className="px-3 py-3">Risk</th><th className="px-3 py-3">Label</th></tr></thead><tbody>{data.items.map((transaction) => <tr key={transaction.transaction_id} className="border-b border-line/70 hover:bg-slate-800/30"><td className="px-3 py-3"><Link className="font-semibold text-blue-300" href={`/transactions/${transaction.transaction_id}`}>{transaction.transaction_id}</Link><p className="mt-1 text-[10px] text-slate-500">{String(transaction.transaction_type)}</p></td><td className="px-3 py-3 text-slate-400">{formatDate(transaction.timestamp)}</td><td className="px-3 py-3 text-slate-300">{transaction.sender_customer_id}</td><td className="px-3 py-3 font-medium text-white">{formatMoney(transaction.amount, String(transaction.currency || 'USD'))}</td><td className="px-3 py-3 text-slate-400">{String(transaction.channel)}</td><td className="px-3 py-3 text-slate-400">{String(transaction.city)}, {String(transaction.country)}</td><td className="px-3 py-3">{transaction.risk_level ? <Badge tone={String(transaction.risk_level)}>{formatNumber(transaction.risk_score, 1)} · {String(transaction.risk_level)}</Badge> : <span className="text-slate-600">Not alerted</span>}</td><td className="px-3 py-3">{transaction.is_fraud ? <Badge tone="red">Synthetic fraud</Badge> : <Badge tone="green">Normal label</Badge>}</td></tr>)}</tbody></table></div>}
      {data && data.pagination.pages > 1 && <div className="mt-4 flex items-center justify-between border-t border-line pt-4 text-xs text-slate-400"><span>Page {data.pagination.page} of {data.pagination.pages}</span><div className="flex gap-2"><Button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button><Button disabled={page >= data.pagination.pages} onClick={() => setPage(page + 1)}>Next</Button></div></div>}
    </Panel>
  </DashboardShell>;
}
