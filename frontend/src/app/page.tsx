import Link from "next/link";
import { ArrowRight, CandlestickChart, Radar, Rows3, Signal, ShieldCheck } from "lucide-react";
import { MetricCard } from "@/components/metric-card";
import { SectionHeading } from "@/components/section-heading";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { getDashboard, formatPercent } from "@/lib/data";

export default function Home() {
  const dashboard = getDashboard();

  return (
    <div className="space-y-8">
      <section className="glass overflow-hidden rounded-[2rem] px-6 py-8 sm:px-8 sm:py-10">
        <div className="flex flex-col gap-8 lg:flex-row lg:items-end lg:justify-between">
          <SectionHeading
            eyebrow="Observability"
            title="See the whole trading research machine without opening a graveyard of folders"
            body="This frontend tracks what was ingested, what got translated into strategy logic, where coverage exists by pair/timeframe, and which leaderboard results deserve trust."
          />

          <div className="grid gap-3 sm:grid-cols-2">
            <Link href="/indicators" className="glass rounded-[1.5rem] p-4 transition hover:border-cyan-300/30">
              <div className="flex items-center justify-between">
                <LayersGlyph />
                <ArrowRight className="h-4 w-4 text-cyan-300" />
              </div>
              <p className="mt-4 text-sm font-medium text-white">Open indicator catalog</p>
              <p className="mt-1 text-sm text-zinc-400">Browse metadata, classifications, and strategy readiness.</p>
            </Link>
            <Link href="/rankings" className="glass rounded-[1.5rem] p-4 transition hover:border-emerald-300/30">
              <div className="flex items-center justify-between">
                <CandlestickChart className="h-5 w-5 text-emerald-300" />
                <ArrowRight className="h-4 w-4 text-emerald-300" />
              </div>
              <p className="mt-4 text-sm font-medium text-white">Inspect rankings</p>
              <p className="mt-1 text-sm text-zinc-400">Compare return, drawdown, sharpe, and caveats.</p>
            </Link>
          </div>
        </div>
      </section>

      <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Indicators" value={dashboard.totals.indicators} hint="Tracked research artifacts" />
        <MetricCard label="Runs" value={dashboard.totals.runs} hint="Immutable run directories" />
        <MetricCard label="Ranked" value={dashboard.totals.ranked} hint="Leaderboard entries with metrics" />
        <MetricCard label="Failed" value={dashboard.totals.failedRuns} hint="Runs that need diagnosis" />
      </section>

      <section className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
        <Card className="glass rounded-[2rem] text-white">
          <CardHeader>
            <CardTitle className="text-lg">Top ranked right now</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {dashboard.topRanked.length === 0 ? (
              <EmptyState body="No ranked runs yet. Push an indicator through ingest → analysis → strategy → backtest → frontend export." />
            ) : (
              dashboard.topRanked.map((item: { indicatorSlug: string; runId: string; totalReturn: number | null; notes: string }) => (
                <div key={item.runId} className="rounded-[1.5rem] border border-white/8 bg-black/10 p-4">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <Link href={`/runs/${item.runId}`} className="text-base font-medium text-white hover:text-cyan-300">
                        {item.indicatorSlug}
                      </Link>
                      <p className="mt-1 text-sm text-zinc-400">Run {item.runId}</p>
                    </div>
                    <Badge className="border-emerald-300/20 bg-emerald-400/10 text-emerald-200">
                      {formatPercent(item.totalReturn)}
                    </Badge>
                  </div>
                  <p className="mt-3 text-sm text-zinc-400">{item.notes || "No caveat note recorded."}</p>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="glass rounded-[2rem] text-white">
          <CardHeader>
            <CardTitle className="text-lg">Recent runs</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {dashboard.recentRuns.length === 0 ? (
              <EmptyState body="Backtest output will show up here once results/runs exists and the frontend indexes are regenerated." />
            ) : (
              dashboard.recentRuns.map((run: { runId: string; indicatorSlug: string; pair: string; timeframe: string }) => (
                <Link
                  key={run.runId}
                  href={`/runs/${run.runId}`}
                  className="flex items-center justify-between rounded-[1.25rem] border border-white/8 bg-black/10 px-4 py-3 transition hover:border-cyan-300/25"
                >
                  <div>
                    <p className="text-sm font-medium text-white">{run.indicatorSlug}</p>
                    <p className="text-sm text-zinc-400">
                      {run.pair || "—"} · {run.timeframe || "—"}
                    </p>
                  </div>
                  <Radar className="h-4 w-4 text-cyan-300" />
                </Link>
              ))
            )}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-6 lg:grid-cols-2">
        <Card className="glass rounded-[2rem] text-white">
          <CardHeader>
            <CardTitle className="text-lg">Status mix</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            {Object.entries(dashboard.statusCounts).map(([status, count]) => (
              <Badge key={status} className="border-white/10 bg-white/8 px-3 py-1.5 text-zinc-200">
                {status}: {count}
              </Badge>
            ))}
          </CardContent>
        </Card>

        <Card className="glass rounded-[2rem] text-white">
          <CardHeader>
            <CardTitle className="text-lg">Classification mix</CardTitle>
          </CardHeader>
          <CardContent className="flex flex-wrap gap-3">
            {Object.entries(dashboard.classificationCounts).map(([classification, count]) => (
              <Badge key={classification} className="border-cyan-400/20 bg-cyan-400/10 px-3 py-1.5 text-cyan-100">
                {classification}: {count}
              </Badge>
            ))}
          </CardContent>
        </Card>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        <QuickLink href="/coverage" label="Coverage matrix" body="See what has actually been tested by pair and timeframe." icon={<Rows3 className="h-5 w-5 text-violet-300" />} />
        <QuickLink href="/rankings" label="Leaderboard" body="Compare return quality with caveats right next to it." icon={<CandlestickChart className="h-5 w-5 text-emerald-300" />} />
        <QuickLink href="/runs" label="Run log" body="Inspect individual assumptions, summaries, and output artifacts." icon={<Radar className="h-5 w-5 text-cyan-300" />} />
        <QuickLink href="/signals" label="Runtime signals" body="Read the real signal feed emitted by promoted runtime strategy versions." icon={<Signal className="h-5 w-5 text-cyan-300" />} />
        <QuickLink href="/ops" label="Runtime ops" body="Track worker heartbeats, lag, and the currently promoted strategy pins." icon={<ShieldCheck className="h-5 w-5 text-emerald-300" />} />
      </section>
    </div>
  );
}

function QuickLink({ href, label, body, icon }: { href: string; label: string; body: string; icon: React.ReactNode }) {
  return (
    <Link href={href} className="glass rounded-[1.75rem] p-5 transition hover:border-white/20">
      <div className="flex items-center justify-between">
        {icon}
        <ArrowRight className="h-4 w-4 text-zinc-500" />
      </div>
      <p className="mt-4 text-base font-medium text-white">{label}</p>
      <p className="mt-2 text-sm leading-6 text-zinc-400">{body}</p>
    </Link>
  );
}

function EmptyState({ body }: { body: string }) {
  return <p className="rounded-[1.25rem] border border-dashed border-white/12 bg-black/10 p-4 text-sm text-zinc-400">{body}</p>;
}

function LayersGlyph() {
  return (
    <div className="relative h-5 w-5">
      <div className="absolute inset-0 rounded-sm border border-cyan-300/60" />
      <div className="absolute inset-1 rounded-sm border border-cyan-300/45" />
      <div className="absolute inset-2 rounded-sm border border-cyan-300/30" />
    </div>
  );
}
