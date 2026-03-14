import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionHeading } from "@/components/section-heading";
import { formatNumber, formatPercent, getExperiments } from "@/lib/data";

export default function ExperimentsPage() {
  const experiments = getExperiments();

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Experiments"
        title="Research is experiment-first now"
        body="Families, variants, and combinations are first-class research units here. This page is the bridge between raw indicator truth and richer strategy experimentation."
      />

      <Card className="glass rounded-[2rem] text-white">
        <CardHeader>
          <CardTitle className="text-lg">Experiment registry</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-white/10 hover:bg-transparent">
                <TableHead className="text-zinc-400">Experiment</TableHead>
                <TableHead className="text-zinc-400">Family</TableHead>
                <TableHead className="text-zinc-400">Kind</TableHead>
                <TableHead className="text-zinc-400">Indicators</TableHead>
                <TableHead className="text-zinc-400">Latest result</TableHead>
                <TableHead className="text-zinc-400">Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {experiments.length === 0 ? (
                <TableRow className="border-white/10 hover:bg-transparent">
                  <TableCell colSpan={6} className="py-10 text-center text-zinc-400">
                    No experiments yet. Seed or run one with <code>tvir experiment &lt;slug&gt;</code>.
                  </TableCell>
                </TableRow>
              ) : (
                experiments.map((experiment) => (
                  <TableRow key={experiment.experimentSlug} className="border-white/10 hover:bg-white/4">
                    <TableCell>
                      <div>
                        <p className="font-medium text-white">{experiment.title}</p>
                        <p className="text-xs text-zinc-500">{experiment.experimentSlug}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <div>
                        <p className="text-sm text-zinc-200">{experiment.family}</p>
                        <p className="text-xs text-zinc-500">{experiment.variant}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className="border-cyan-300/20 bg-cyan-400/10 text-cyan-100">{experiment.kind}</Badge>
                    </TableCell>
                    <TableCell className="text-sm text-zinc-300">{experiment.indicators.join(", ")}</TableCell>
                    <TableCell>
                      {experiment.latestRunId ? (
                        <div>
                          <Link href={`/runs/${experiment.latestRunId}`} className="text-sm font-medium text-cyan-300 hover:text-cyan-200">
                            {formatPercent(asNumber(experiment.latestMetrics?.total_return))}
                          </Link>
                          <p className="text-xs text-zinc-500">
                            Sharpe {formatNumber(asNumber(experiment.latestMetrics?.sharpe_ratio))} · Trades {formatNumber(asNumber(experiment.latestMetrics?.trade_count))}
                          </p>
                        </div>
                      ) : (
                        <span className="text-sm text-zinc-500">No run yet</span>
                      )}
                    </TableCell>
                    <TableCell>
                      <Badge className="border-white/10 bg-white/8 text-zinc-200">{experiment.status}</Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <section className="grid gap-4 lg:grid-cols-2">
        {experiments.slice(0, 4).map((experiment) => (
          <Card key={experiment.experimentSlug} className="glass rounded-[2rem] text-white">
            <CardHeader>
              <CardTitle className="text-lg">{experiment.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm text-zinc-300">
              <div className="flex flex-wrap gap-2">
                <Badge className="border-cyan-300/20 bg-cyan-400/10 text-cyan-100">{experiment.family}</Badge>
                <Badge className="border-emerald-300/20 bg-emerald-400/10 text-emerald-100">{experiment.kind}</Badge>
                {experiment.tags.map((tag) => (
                  <Badge key={tag} className="border-white/10 bg-white/8 text-zinc-200">{tag}</Badge>
                ))}
              </div>
              <p>{experiment.rationale || experiment.notes || "No rationale recorded."}</p>
              <p className="text-zinc-400">Indicators: {experiment.indicators.join(", ")}</p>
              <p className="text-zinc-400">Filters: {experiment.filters.join(", ") || "—"}</p>
              <p className="text-zinc-400">Exits: {experiment.exits.join(", ") || "—"}</p>
            </CardContent>
          </Card>
        ))}
      </section>
    </div>
  );
}

function asNumber(value: unknown): number | null {
  return typeof value === "number" ? value : null;
}
