import { notFound } from "next/navigation";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { formatNumber, formatPercent, getRun } from "@/lib/data";

export default function RunDetailPage({ params }: { params: { runId: string } }) {
  const run = getRun(params.runId);
  if (!run) notFound();

  return (
    <div className="space-y-6">
      <Card className="glass rounded-[2rem] text-white">
        <CardHeader>
          <div className="flex flex-wrap items-center gap-3">
            <Badge className="border-cyan-300/20 bg-cyan-400/10 text-cyan-100">{run.indicatorSlug}</Badge>
            <Badge className="border-white/10 bg-white/8 text-zinc-300">{run.exchange}</Badge>
          </div>
          <CardTitle className="mt-4 text-2xl">{run.runId}</CardTitle>
          <p className="text-sm text-zinc-400">
            {run.pair} · {run.timeframe} · fees {run.feesBps ?? "—"}bps · slippage {run.slippageBps ?? "—"}bps
          </p>
        </CardHeader>
      </Card>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="glass rounded-[2rem] text-white">
          <CardHeader>
            <CardTitle className="text-lg">Metrics</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-3 sm:grid-cols-2">
            <Metric label="Total return" value={formatPercent(typeof run.metrics.total_return === "number" ? run.metrics.total_return : null)} />
            <Metric label="Max drawdown" value={formatPercent(typeof run.metrics.max_drawdown === "number" ? run.metrics.max_drawdown : null)} />
            <Metric label="Sharpe ratio" value={formatNumber(typeof run.metrics.sharpe_ratio === "number" ? run.metrics.sharpe_ratio : null)} />
            <Metric label="Win rate" value={formatPercent(typeof run.metrics.win_rate === "number" ? run.metrics.win_rate : null)} />
            <Metric label="Trade count" value={String(run.metrics.trade_count ?? "—")} />
            <Metric label="Engine note" value={String(run.metrics.notes ?? "—")} />
          </CardContent>
        </Card>

        <Card className="glass rounded-[2rem] text-white">
          <CardHeader>
            <CardTitle className="text-lg">Assumptions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 text-sm text-zinc-300">
            <p>
              <span className="text-zinc-500">Date range:</span>{" "}
              {run.dateRange?.start || "—"} → {run.dateRange?.end || "—"}
            </p>
            <Separator className="bg-white/10" />
            <pre className="overflow-x-auto rounded-[1.25rem] border border-white/8 bg-black/20 p-4 text-xs leading-6 text-zinc-300 whitespace-pre-wrap">
              {run.summary || "No summary found."}
            </pre>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-[1.25rem] border border-white/8 bg-black/10 p-4">
      <p className="text-xs uppercase tracking-[0.3em] text-zinc-500">{label}</p>
      <p className="mt-2 text-xl font-semibold text-white">{value}</p>
    </div>
  );
}
