import Link from "next/link";
import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { getIndicator, getIndicatorRuns } from "@/lib/data";

export default function IndicatorDetailPage({ params }: { params: { slug: string } }) {
  const indicator = getIndicator(params.slug);
  if (!indicator) notFound();
  const runs = getIndicatorRuns(indicator.slug);

  return (
    <div className="space-y-6">
      <Card className="glass rounded-[2rem] text-white">
        <CardHeader className="space-y-4">
          <div className="flex flex-wrap items-center gap-3">
            <Badge className="border-cyan-300/20 bg-cyan-400/10 text-cyan-100">{indicator.classification}</Badge>
            <Badge className="border-emerald-300/20 bg-emerald-400/10 text-emerald-100">{indicator.status}</Badge>
            <Badge className="border-white/10 bg-white/6 text-zinc-300">{indicator.pineVersion || "Pine unknown"}</Badge>
          </div>
          <div>
            <p className="text-[11px] uppercase tracking-[0.35em] text-cyan-300/70">Indicator detail</p>
            <h1 className="mt-3 text-3xl font-semibold tracking-tight text-white">{indicator.title}</h1>
            <p className="mt-2 text-sm text-zinc-400">by {indicator.author}</p>
          </div>
          <p className="max-w-3xl text-sm leading-7 text-zinc-300">
            {indicator.analysis.summary || indicator.notes || "No analysis summary yet."}
          </p>
        </CardHeader>
      </Card>

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card className="glass rounded-[2rem] text-white">
          <CardHeader>
            <CardTitle className="text-lg">Metadata + caveats</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-zinc-300">
            <MetaRow label="Source section" value={indicator.discoveredFrom || "—"} />
            <MetaRow label="Script type" value={indicator.scriptType} />
            <MetaRow label="Repaint risk" value={indicator.repaintRisk} />
            <MetaRow label="Signal model" value={indicator.analysis.signalModel || "—"} />
            <Separator className="bg-white/10" />
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Caution flags</p>
              <div className="mt-3 flex flex-wrap gap-2">
                {indicator.analysis.cautionFlags.length === 0 ? (
                  <Badge className="border-white/10 bg-white/6 text-zinc-300">None recorded</Badge>
                ) : (
                  indicator.analysis.cautionFlags.map((flag) => (
                    <Badge key={flag} className="border-amber-300/20 bg-amber-400/10 text-amber-100">
                      {flag}
                    </Badge>
                  ))
                )}
              </div>
            </div>
            <div>
              <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">Translation notes</p>
              <p className="mt-2 leading-7 text-zinc-400">
                {indicator.analysis.translationNotes || "No translation notes recorded yet."}
              </p>
            </div>
            {indicator.sourceUrl ? (
              <Link href={indicator.sourceUrl} target="_blank" className="text-cyan-300 hover:text-cyan-200">
                Open TradingView source
              </Link>
            ) : null}
          </CardContent>
        </Card>

        <Card className="glass rounded-[2rem] text-white">
          <CardHeader>
            <CardTitle className="text-lg">Run history</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {runs.length === 0 ? (
              <p className="rounded-[1.25rem] border border-dashed border-white/12 bg-black/10 p-4 text-sm text-zinc-400">
                No runs yet. Once this indicator is strategy-ready and tested, the history will appear here.
              </p>
            ) : (
              runs.map((run) => (
                <Link key={run.runId} href={`/runs/${run.runId}`} className="block rounded-[1.25rem] border border-white/8 bg-black/10 p-4 transition hover:border-cyan-300/25">
                  <div className="flex items-start justify-between gap-4">
                    <div>
                      <p className="font-medium text-white">{run.runId}</p>
                      <p className="mt-1 text-sm text-zinc-400">
                        {run.pair} · {run.timeframe}
                      </p>
                    </div>
                    <Badge className="border-emerald-300/20 bg-emerald-400/10 text-emerald-100">
                      {typeof run.metrics.total_return === "number" ? `${run.metrics.total_return.toFixed(2)}%` : "—"}
                    </Badge>
                  </div>
                </Link>
              ))
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function MetaRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 rounded-[1rem] border border-white/8 bg-black/10 px-4 py-3">
      <span className="text-zinc-400">{label}</span>
      <span className="text-right text-white">{value}</span>
    </div>
  );
}
