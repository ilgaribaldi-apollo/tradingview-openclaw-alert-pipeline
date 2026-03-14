import Link from "next/link";
import { Activity, CandlestickChart, Layers3, Radar, Rows3 } from "lucide-react";

const nav = [
  { href: "/", label: "Overview", icon: Activity },
  { href: "/indicators", label: "Indicators", icon: Layers3 },
  { href: "/coverage", label: "Coverage", icon: Rows3 },
  { href: "/rankings", label: "Rankings", icon: CandlestickChart },
  { href: "/runs", label: "Runs", icon: Radar },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[radial-gradient(circle_at_top,#15192a_0%,#090b12_35%,#05060a_100%)] text-white">
      <div className="mx-auto flex min-h-screen max-w-7xl gap-6 px-4 py-6 sm:px-6 lg:px-8">
        <aside className="sticky top-6 hidden h-[calc(100vh-3rem)] w-72 shrink-0 rounded-[2rem] border border-white/10 bg-white/5 p-5 backdrop-blur-xl lg:flex lg:flex-col">
          <div>
            <p className="text-[11px] uppercase tracking-[0.35em] text-cyan-300/70">TradingView Research</p>
            <h1 className="mt-3 font-mono text-2xl font-semibold tracking-tight text-white">
              Observatory
            </h1>
            <p className="mt-3 text-sm leading-6 text-zinc-400">
              Internal dashboard for indicator intake, strategy readiness, coverage, and
              comparative backtest quality.
            </p>
          </div>

          <nav className="mt-8 space-y-2">
            {nav.map(({ href, label, icon: Icon }) => (
              <Link
                key={href}
                href={href}
                className="group flex items-center justify-between rounded-2xl border border-white/6 bg-black/10 px-4 py-3 text-sm text-zinc-300 transition hover:border-cyan-300/30 hover:bg-cyan-400/8 hover:text-white"
              >
                <span className="flex items-center gap-3">
                  <Icon className="h-4 w-4 text-cyan-300/80 transition group-hover:scale-110" />
                  {label}
                </span>
                <span className="text-[10px] uppercase tracking-[0.3em] text-zinc-500">Open</span>
              </Link>
            ))}
          </nav>

          <div className="mt-auto rounded-[1.75rem] border border-emerald-400/15 bg-emerald-400/8 p-4">
            <p className="text-[10px] uppercase tracking-[0.32em] text-emerald-300/80">Operator rule</p>
            <p className="mt-2 text-sm leading-6 text-emerald-50/90">
              Surface caveats near rankings. Pretty charts are not evidence.
            </p>
          </div>
        </aside>

        <main className="min-w-0 flex-1">{children}</main>
      </div>
    </div>
  );
}
