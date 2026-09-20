'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { BookOpen, Database, FileSearch, Gauge, GitBranch, Lightbulb, ListFilter, Network, Radar, Settings2, ShieldAlert, Users, Workflow } from 'lucide-react';
import type { ReactNode } from 'react';

const navigation = [
  { label: 'Overview', href: '/overview', icon: Gauge },
  { label: 'Alert Queue', href: '/alerts', icon: ListFilter },
  { label: 'Transaction Explorer', href: '/transactions', icon: FileSearch },
  { label: 'Customer Risk', href: '/customers', icon: Users },
  { label: 'Network Analysis', href: '/network', icon: Network },
  { label: 'Rule Performance', href: '/rules', icon: Radar },
  { label: 'Rule Tuning', href: '/rules/tuning', icon: Settings2 },
  { label: 'Model Evaluation', href: '/models', icon: GitBranch },
  { label: 'Investigations', href: '/investigations', icon: Workflow },
  { label: 'Data Quality', href: '/data-quality', icon: Database },
  { label: 'Insights', href: '/insights', icon: Lightbulb },
  { label: 'Documentation', href: '/documentation', icon: BookOpen },
];

export default function DashboardShell({ children, title, subtitle, actions }: { children: ReactNode; title: string; subtitle?: string; actions?: ReactNode }) {
  const pathname = usePathname();
  return <div className="min-h-screen bg-navy text-slate-200"><div className="mx-auto flex min-h-screen max-w-[1600px]">
    <aside className="hidden w-64 shrink-0 border-r border-line bg-[#091726] p-5 lg:block">
      <Link href="/overview" className="mb-8 flex items-center gap-3 px-2"><div className="rounded-lg bg-blue-500/15 p-2 text-blue-300"><ShieldAlert size={20} /></div><div><p className="text-sm font-semibold text-white">Fraud Command</p><p className="text-xs text-slate-500">Center</p></div></Link>
      <nav className="space-y-1">{navigation.map(({ label, href, icon: Icon }) => { const active = pathname === href || (href !== '/overview' && pathname.startsWith(href)); return <Link href={href} key={href} className={`flex items-center gap-3 rounded-md px-3 py-2.5 text-xs transition ${active ? 'bg-blue-500/15 text-blue-200' : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-100'}`}><Icon size={15} />{label}</Link>; })}</nav>
      <div className="mt-10 rounded-lg border border-amber-400/20 bg-amber-400/5 p-3 text-[10px] leading-5 text-amber-100/70">Synthetic data only. Risk scores prioritize human review and do not prove fraud.</div>
    </aside>
    <main className="min-w-0 flex-1 p-4 md:p-7">
      <div className="mb-5 flex gap-2 overflow-x-auto pb-1 lg:hidden">{navigation.slice(0, 6).map(({ label, href }) => <Link key={href} href={href} className={`whitespace-nowrap rounded-md border px-3 py-2 text-[11px] ${pathname.startsWith(href) ? 'border-blue-400/40 bg-blue-500/15 text-blue-100' : 'border-line text-slate-400'}`}>{label}</Link>)}</div>
      <header className="mb-7 flex flex-col justify-between gap-4 border-b border-line pb-6 xl:flex-row xl:items-start"><div><p className="mb-2 text-[10px] font-semibold uppercase tracking-[0.2em] text-blue-300">Risk operations workspace</p><h1 className="text-2xl font-semibold tracking-tight text-white md:text-3xl">{title}</h1>{subtitle && <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">{subtitle}</p>}</div><div className="flex items-center gap-3">{actions}<span className="rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-[10px] font-semibold text-amber-200">Synthetic portfolio data</span></div></header>
      {children}
    </main>
  </div></div>;
}
