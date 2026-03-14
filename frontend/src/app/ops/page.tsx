import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { SectionHeading } from "@/components/section-heading";
import { formatNumber, getRuntimeOps } from "@/lib/data";

export default function OpsPage() {
  const snapshot = getRuntimeOps();

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Runtime boundary"
        title="Worker health, lag, and promoted pins"
        body="Low-noise ops view over the runtime registry and worker heartbeat read models. This is meant to answer one question fast: is the promoted runtime path actually alive?"
      />

      <section className="grid gap-4 lg:grid-cols-[1.15fr_0.85fr]">
        <Card className="glass rounded-[2rem] text-white">
          <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <CardTitle className="text-lg">Worker heartbeat overview</CardTitle>
              <p className="mt-2 text-sm text-zinc-400">Generated {formatDateTime(snapshot.generatedAt)}</p>
            </div>
            <StatusBadge status={snapshot.status} />
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.status !== "ok" ? (
              <EmptyState body={snapshot.error || "Runtime ops snapshot is unavailable right now."} />
            ) : snapshot.items.length === 0 ? (
              <EmptyState body="No worker heartbeats yet. Run the market-data/signals/ops workers and export again." />
            ) : (
              snapshot.items.map((row) => (
                <div key={`${row.lane}-${row.worker_name}`} className="rounded-[1.5rem] border border-white/8 bg-black/10 p-4">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p className="font-medium text-white">{row.worker_name}</p>
                      <p className="mt-1 text-sm text-zinc-500">Lane: {row.lane}</p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <Badge className={statusTone(row.status)}>{row.status}</Badge>
                      <Badge className="border-white/10 bg-white/8 text-zinc-200">lag {formatLag(row.lag_seconds)}</Badge>
                    </div>
                  </div>
                  <div className="mt-4 grid gap-2 text-sm text-zinc-400 sm:grid-cols-2">
                    <p>Heartbeat: {formatDateTime(row.heartbeat_at)}</p>
                    <p>Tracked feeds: {formatNumber(row.tracked_feeds)}</p>
                    <p className="sm:col-span-2">Error: {row.error_summary || "—"}</p>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        <Card className="glass rounded-[2rem] text-white">
          <CardHeader>
            <CardTitle className="text-lg">Promoted strategy registry</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {snapshot.promotedStrategies.length === 0 ? (
              <EmptyState body="No runtime-enabled promoted strategies found in the registry." />
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
                    <Badge className="border-cyan-300/20 bg-cyan-400/10 text-cyan-100">{row.stage}</Badge>
                  </div>
                  <div className="mt-4 space-y-1 text-sm text-zinc-400">
                    <p>Verdict: {row.latest_verdict || "—"}</p>
                    <p>Coverage: {row.coverage_status || "—"}</p>
                    <p>Trade count: {formatNumber(row.trade_count)}</p>
                    <p>Rationale: {row.latest_rationale || "—"}</p>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>
      </section>
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

function statusTone(status: string) {
  if (status === "running") return "border-emerald-300/20 bg-emerald-400/10 text-emerald-100";
  if (status === "degraded") return "border-amber-300/20 bg-amber-400/10 text-amber-100";
  if (status === "failed") return "border-rose-300/20 bg-rose-400/10 text-rose-100";
  return "border-white/10 bg-white/8 text-zinc-200";
}

function formatLag(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value}s`;
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
