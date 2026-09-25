'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { Search, Users } from 'lucide-react';
import DashboardShell from '@/components/dashboard-shell';
import { apiFetch, queryString } from '@/lib/api';
import type { Paginated } from '@/lib/types';
import { Badge, Button, EmptyState, ErrorState, LoadingState, Panel, Select, formatMoney, formatNumber } from '@/components/ui';

type Customer = Record<string, unknown> & { customer_id: string; anonymized_name: string; customer_risk_level: string; customer_type: string };

export default function CustomersPage() {
  const [data, setData] = useState<Paginated<Customer> | null>(null);
  const [search, setSearch] = useState('');
  const [risk, setRisk] = useState('');
  const [type, setType] = useState('');
  const [page, setPage] = useState(1);
  const [error, setError] = useState('');
  const load = () => apiFetch<Paginated<Customer>>(`/api/customers${queryString({ page, page_size: 25, search, risk_level: risk, customer_type: type })}`).then(setData).catch((reason) => setError(reason.message));
  useEffect(() => { load(); }, [page, risk, type]);
  return <DashboardShell title="Customer Risk" subtitle="Customer 360 view starts here: profile risk, transaction volume, alert activity and links to individual customer timelines.">
    <Panel title="Customer filters" eyebrow="Population view"><div className="flex flex-wrap gap-3"><div className="relative min-w-[260px] flex-1"><Search size={15} className="absolute left-3 top-2.5 text-slate-500" /><input value={search} onChange={(event) => setSearch(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && (setPage(1), load())} placeholder="Search customer ID or anonymized name" className="w-full rounded-md border border-line bg-slate-900 py-2 pl-9 pr-3 text-xs text-slate-200 outline-none" /></div><Select value={risk} onChange={(value) => { setRisk(value); setPage(1); }}><option value="">All profile risks</option><option>Low</option><option>Medium</option><option>High</option></Select><Select value={type} onChange={(value) => { setType(value); setPage(1); }}><option value="">All customer types</option><option>standard_customer</option><option>high_value_customer</option><option>small_business</option><option>new_customer</option></Select><Button onClick={() => { setPage(1); load(); }}>Apply filters</Button></div></Panel>
    <Panel className="mt-4" title="Customer population" eyebrow={`${formatNumber(data?.pagination.total || 0)} customers`}>
      {error ? <ErrorState message={error} /> : !data ? <LoadingState /> : data.items.length === 0 ? <EmptyState /> : <div className="overflow-x-auto"><table className="w-full min-w-[900px] text-left text-xs"><thead className="border-b border-line text-[10px] uppercase tracking-wide text-slate-500"><tr><th className="px-3 py-3">Customer</th><th className="px-3 py-3">Segment</th><th className="px-3 py-3">Profile risk</th><th className="px-3 py-3">Transactions</th><th className="px-3 py-3">Total volume</th><th className="px-3 py-3">Average amount</th><th className="px-3 py-3">Alerts</th></tr></thead><tbody>{data.items.map((customer) => <tr key={customer.customer_id} className="border-b border-line/70 hover:bg-slate-800/30"><td className="px-3 py-3"><Link href={`/customers/${customer.customer_id}`} className="flex items-center gap-2 font-semibold text-blue-300"><Users size={14} />{customer.customer_id}</Link><p className="mt-1 text-[10px] text-slate-500">{customer.anonymized_name}</p></td><td className="px-3 py-3 text-slate-400">{customer.customer_type}</td><td className="px-3 py-3"><Badge tone={customer.customer_risk_level}>{customer.customer_risk_level}</Badge></td><td className="px-3 py-3 text-slate-300">{formatNumber(customer.transaction_count)}</td><td className="px-3 py-3 font-medium text-white">{formatMoney(customer.total_volume)}</td><td className="px-3 py-3 text-slate-400">{formatMoney(customer.average_amount)}</td><td className="px-3 py-3 text-slate-400">{formatNumber(customer.alert_count)}</td></tr>)}</tbody></table></div>}
      {data && data.pagination.pages > 1 && <div className="mt-4 flex items-center justify-between border-t border-line pt-4 text-xs text-slate-400"><span>Page {page} of {data.pagination.pages}</span><div className="flex gap-2"><Button disabled={page <= 1} onClick={() => setPage(page - 1)}>Previous</Button><Button disabled={page >= data.pagination.pages} onClick={() => setPage(page + 1)}>Next</Button></div></div>}
    </Panel>
  </DashboardShell>;
}
