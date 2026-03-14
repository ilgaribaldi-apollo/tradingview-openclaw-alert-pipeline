import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionHeading } from "@/components/section-heading";
import { formatNumber, getRuntimeSignals } from "@/lib/data";

export default function SignalsPage() {
  const snapshot = getRuntimeSignals();

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Runtime boundary"
        title="Recent signal feed from promoted strategy versions"
        body="This page is sourced from the runtime read model snapshot, not the research leaderboard. If a strategy was not promoted and pinned, it should not show up here."
      />

      <Card className="glass rounded-[2rem] text-white">
        <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <CardTitle className="text-lg">Signal feed</CardTitle>
            <p className="mt-2 text-sm text-zinc-400">Generated {formatDateTime(snapshot.generatedAt)}</p>
          </div>
          <StatusBadge status={snapshot.status} />
        </CardHeader>
        <CardContent>
          {snapshot.status !== "ok" ? (
            <EmptyState body={snapshot.error || "Runtime read models are unavailable right now."} />
          ) : snapshot.items.length === 0 ? (
            <EmptyState body="No recent signals yet. Promote a strategy, run the signals worker, and export the frontend indexes again." />
          ) : (
            <Table>
              <TableHeader>
                <TableRow className="border-white/10 hover:bg-transparent">
                  <TableHead className="text-zinc-400">When</TableHead>
                  <TableHead className="text-zinc-400">Strategy</TableHead>
                  <TableHead className="text-zinc-400">Market</TableHead>
                  <TableHead className="text-zinc-400">Type</TableHead>
                  <TableHead className="text-zinc-400">Source</TableHead>
                  <TableHead className="text-right text-zinc-400">Price</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {snapshot.items.map((row) => (
                  <TableRow key={row.id} className="border-white/10 hover:bg-white/4">
                    <TableCell className="text-sm text-zinc-300">{formatDateTime(row.signal_at)}</TableCell>
                    <TableCell>
                      <div>
                        <p className="font-medium text-white">{row.strategy_title || row.strategy_slug}</p>
                        <p className="text-xs text-zinc-500">
                          {row.strategy_slug}@{row.strategy_version}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-zinc-300">
                      {row.venue}:{row.symbol}:{row.timeframe}
                    </TableCell>
                    <TableCell>
                      <Badge className="border-cyan-300/20 bg-cyan-400/10 text-cyan-100">{row.signal_type}</Badge>
                    </TableCell>
                    <TableCell className="text-sm text-zinc-400">{row.signal_source}</TableCell>
                    <TableCell className="text-right text-sm text-zinc-200">{formatNumber(row.price)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      <Card className="glass rounded-[2rem] text-white">
        <CardHeader>
          <CardTitle className="text-lg">Promoted strategy pins</CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {snapshot.promotedStrategies.length === 0 ? (
            <EmptyState body="No promoted strategy pins recorded in the runtime registry yet." />
          ) : (
            snapshot.promotedStrategies.map((row) => (
              <div key={`${row.slug}-${row.version}`} className="rounded-[1.5rem] border border-white/8 bg-black/10 p-4">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-medium text-white">{row.title || row.slug}</p>
                    <p className="mt-1 text-xs text-zinc-500">
                      {row.slug}@{row.version}
                    </p>
                  </div>
                  <Badge className="border-emerald-300/20 bg-emerald-400/10 text-emerald-100">{row.stage}</Badge>
                </div>
                <div className="mt-4 space-y-1 text-sm text-zinc-400">
                  <p>Verdict: {row.latest_verdict || "—"}</p>
                  <p>
                    Market: {row.pair || "—"} · {row.timeframe || "—"}
                  </p>
                  <p>
                    Return / Sharpe: {formatNumber(row.total_return)} / {formatNumber(row.sharpe_ratio)}
                  </p>
                </div>
              </div>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function StatusBadge({ status }: { status: string }) {
  const tone = status === "ok" ? "border-emerald-300/20 bg-emerald-400/10 text-emerald-100" : "border-amber-300/20 bg-amber-400/10 text-amber-100";
  return <Badge className={tone}>{status}</Badge>;
}

function EmptyState({ body }: { body: string }) {
  return <p className="rounded-[1.25rem] border border-dashed border-white/12 bg-black/10 p-4 text-sm text-zinc-400">{body}</p>;
}

function formatDateTime(value: string | null | undefined) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("en-US", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date);
}
