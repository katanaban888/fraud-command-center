import { Activity, ShieldAlert, Sparkles } from 'lucide-react';

const navigation = ['Overview', 'Alert Queue', 'Transaction Explorer', 'Customer Risk', 'Network Analysis'];

export default function HomePage() {
  return (
    <main className="min-h-screen bg-navy">
      <div className="mx-auto flex min-h-screen max-w-[1440px]">
        <aside className="hidden w-64 border-r border-line bg-[#091726] p-6 lg:block">
          <div className="mb-10 flex items-center gap-3">
            <div className="rounded-lg bg-blue-500/15 p-2 text-blue-300"><ShieldAlert size={20} /></div>
            <div>
              <p className="text-sm font-semibold text-white">Fraud Command</p>
              <p className="text-xs text-slate-400">Center</p>
            </div>
          </div>
          <nav className="space-y-1">
            {navigation.map((item, index) => (
              <div key={item} className={`rounded-md px-3 py-2 text-sm ${index === 0 ? 'bg-blue-500/15 text-blue-200' : 'text-slate-400'}`}>
                {item}
              </div>
            ))}
          </nav>
        </aside>
        <section className="flex-1 p-6 md:p-10">
          <div className="mx-auto max-w-6xl">
            <div className="mb-10 flex flex-col justify-between gap-4 md:flex-row md:items-start">
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.2em] text-blue-300">Risk operations workspace</p>
                <h1 className="text-3xl font-semibold tracking-tight text-white md:text-4xl">Fraud Command Center</h1>
                <p className="mt-3 max-w-2xl text-slate-400">Explainable transaction monitoring and risk-based alert prioritization.</p>
              </div>
              <div className="flex items-center gap-2 rounded-full border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-xs text-amber-200">
                <Sparkles size={14} /> Synthetic portfolio dataset
              </div>
            </div>
            <div className="grid gap-4 md:grid-cols-3">
              {[
                ['Pipeline status', 'Phase 1 ready', 'Data generation and schema are being built.'],
                ['Default storage', 'SQLite', 'PostgreSQL-compatible data layer planned.'],
                ['API status', 'FastAPI scaffold', 'Health endpoint is available after backend start.'],
              ].map(([label, value, detail]) => (
                <article key={label} className="rounded-xl border border-line bg-panel p-5 shadow-2xl shadow-black/10">
                  <div className="mb-6 flex items-center justify-between">
                    <span className="text-sm text-slate-400">{label}</span>
                    <Activity size={17} className="text-blue-300" />
                  </div>
                  <p className="text-2xl font-semibold text-white">{value}</p>
                  <p className="mt-2 text-sm leading-6 text-slate-500">{detail}</p>
                </article>
              ))}
            </div>
            <div className="mt-6 rounded-xl border border-line bg-panel p-6">
              <h2 className="text-lg font-semibold text-white">Demo workspace</h2>
              <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-400">
                Dashboard data will be based on synthetic transactions generated for portfolio demonstration. The next phases add the alert queue, explainable rules, customer 360 and investigation workflow.
              </p>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}
