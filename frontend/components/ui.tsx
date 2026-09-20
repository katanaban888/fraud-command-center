'use client';

import Link from 'next/link';
import { AlertCircle, ArrowDown, ArrowUp, CheckCircle2, Loader2 } from 'lucide-react';
import type { ReactNode } from 'react';

export function Panel({ title, eyebrow, action, children, className = '' }: { title?: string; eyebrow?: string; action?: ReactNode; children: ReactNode; className?: string }) {
  return (
    <section className={`rounded-xl border border-line bg-panel shadow-xl shadow-black/10 ${className}`}>
      {(title || eyebrow || action) && (
        <div className="flex items-start justify-between gap-4 border-b border-line px-5 py-4">
          <div>
            {eyebrow && <p className="mb-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-blue-300">{eyebrow}</p>}
            {title && <h2 className="text-sm font-semibold text-white">{title}</h2>}
          </div>
          {action}
        </div>
      )}
      <div className="p-5">{children}</div>
    </section>
  );
}

export function MetricCard({ label, value, detail, tone = 'blue', icon }: { label: string; value: ReactNode; detail?: string; tone?: 'blue' | 'amber' | 'red' | 'green' | 'slate'; icon?: ReactNode }) {
  const tones = {
    blue: 'border-blue-400/20 bg-blue-400/[0.07] text-blue-200',
    amber: 'border-amber-400/20 bg-amber-400/[0.07] text-amber-200',
    red: 'border-red-400/20 bg-red-400/[0.07] text-red-200',
    green: 'border-emerald-400/20 bg-emerald-400/[0.07] text-emerald-200',
    slate: 'border-line bg-panel text-slate-200',
  };
  return (
    <article className={`rounded-xl border p-4 ${tones[tone]}`}>
      <div className="mb-4 flex items-center justify-between text-xs text-slate-400">
        <span>{label}</span>
        {icon}
      </div>
      <p className="text-2xl font-semibold tracking-tight text-white">{value}</p>
      {detail && <p className="mt-2 text-xs leading-5 text-slate-500">{detail}</p>}
    </article>
  );
}

export function Badge({ children, tone = 'slate' }: { children: ReactNode; tone?: string }) {
  const toneClass = tone.toLowerCase().includes('critical') || tone.toLowerCase().includes('fraud') || tone === 'red'
    ? 'border-red-400/30 bg-red-400/10 text-red-200'
    : tone.toLowerCase().includes('high') || tone.toLowerCase().includes('p1') || tone === 'orange'
      ? 'border-orange-400/30 bg-orange-400/10 text-orange-200'
      : tone.toLowerCase().includes('medium') || tone.toLowerCase().includes('p2') || tone === 'amber'
        ? 'border-amber-400/30 bg-amber-400/10 text-amber-200'
        : tone.toLowerCase().includes('low') || tone.toLowerCase().includes('closed') || tone === 'green'
          ? 'border-emerald-400/30 bg-emerald-400/10 text-emerald-200'
          : 'border-slate-400/20 bg-slate-400/10 text-slate-300';
  return <span className={`inline-flex items-center rounded-full border px-2 py-1 text-[10px] font-semibold uppercase tracking-wide ${toneClass}`}>{children}</span>;
}

export function LoadingState({ label = 'Loading analytical data…' }: { label?: string }) {
  return <div className="flex min-h-40 items-center justify-center gap-2 text-sm text-slate-400"><Loader2 size={17} className="animate-spin text-blue-300" />{label}</div>;
}

export function ErrorState({ message }: { message: string }) {
  return <div className="flex min-h-32 items-center gap-3 rounded-lg border border-red-400/20 bg-red-400/5 p-4 text-sm text-red-200"><AlertCircle size={18} />{message}</div>;
}

export function EmptyState({ message = 'No records match the current filters.' }: { message?: string }) {
  return <div className="flex min-h-32 items-center justify-center gap-2 text-sm text-slate-500"><CheckCircle2 size={17} className="text-slate-600" />{message}</div>;
}

export function SortIndicator({ direction }: { direction?: 'asc' | 'desc' }) {
  return direction === 'asc' ? <ArrowUp size={13} /> : direction === 'desc' ? <ArrowDown size={13} /> : null;
}

export function formatNumber(value: unknown, digits = 0) {
  const number = Number(value || 0);
  return new Intl.NumberFormat('en-US', { maximumFractionDigits: digits, minimumFractionDigits: digits }).format(number);
}

export function formatMoney(value: unknown, currency = 'USD') {
  const number = Number(value || 0);
  return new Intl.NumberFormat('en-US', { style: 'currency', currency, maximumFractionDigits: 0 }).format(number);
}

export function formatDate(value: unknown) {
  if (!value) return '—';
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? String(value) : date.toLocaleString('en-US', { dateStyle: 'medium', timeStyle: 'short' });
}

export function Button({ children, href, onClick, variant = 'secondary', type = 'button', disabled = false }: { children: ReactNode; href?: string; onClick?: () => void; variant?: 'primary' | 'secondary' | 'danger' | 'ghost'; type?: 'button' | 'submit'; disabled?: boolean }) {
  const classes = {
    primary: 'border-blue-400/30 bg-blue-500/20 text-blue-100 hover:bg-blue-500/30',
    secondary: 'border-line bg-slate-800/70 text-slate-200 hover:border-blue-400/30 hover:text-white',
    danger: 'border-red-400/30 bg-red-400/10 text-red-100 hover:bg-red-400/20',
    ghost: 'border-transparent text-slate-400 hover:bg-slate-800/60 hover:text-white',
  };
  const className = `inline-flex items-center justify-center rounded-md border px-3 py-2 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${classes[variant]}`;
  if (href) return <Link className={className} href={href}>{children}</Link>;
  return <button className={className} onClick={onClick} type={type} disabled={disabled}>{children}</button>;
}

export function Select({ value, onChange, children, className = '' }: { value: string; onChange: (value: string) => void; children: ReactNode; className?: string }) {
  return <select value={value} onChange={(event) => onChange(event.target.value)} className={`rounded-md border border-line bg-slate-900/80 px-3 py-2 text-xs text-slate-200 outline-none focus:border-blue-400/50 ${className}`}>{children}</select>;
}
