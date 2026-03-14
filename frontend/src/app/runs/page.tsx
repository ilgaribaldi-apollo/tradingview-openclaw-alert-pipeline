import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionHeading } from "@/components/section-heading";
import { formatPercent, getRuns } from "@/lib/data";

export default function RunsPage() {
  const runs = getRuns();

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Runs"
        title="Run log"
        body="Immutable run artifacts are the heartbeat of this project. If a result cannot be traced back to a run directory, it does not count."
      />

      <Card className="glass rounded-[2rem] text-white">
        <CardHeader>
          <CardTitle className="text-lg">All runs</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-white/10 hover:bg-transparent">
                <TableHead className="text-zinc-400">Run</TableHead>
                <TableHead className="text-zinc-400">Indicator</TableHead>
                <TableHead className="text-zinc-400">Pair / TF</TableHead>
                <TableHead className="text-zinc-400">Return</TableHead>
                <TableHead className="text-zinc-400">Engine note</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {runs.length === 0 ? (
                <TableRow className="border-white/10 hover:bg-transparent">
                  <TableCell colSpan={5} className="py-10 text-center text-zinc-400">
                    No runs yet.
                  </TableCell>
                </TableRow>
              ) : (
                runs.map((run) => (
                  <TableRow key={run.runId} className="border-white/10 hover:bg-white/4">
                    <TableCell>
                      <Link href={`/runs/${run.runId}`} className="font-medium text-white hover:text-cyan-300">
                        {run.runId}
                      </Link>
                    </TableCell>
                    <TableCell>
                      <Link href={`/indicators/${run.indicatorSlug}`} className="text-zinc-300 hover:text-white">
                        {run.indicatorSlug}
                      </Link>
                    </TableCell>
                    <TableCell className="text-zinc-300">{run.pair} · {run.timeframe}</TableCell>
                    <TableCell className="text-emerald-300">{formatPercent(typeof run.metrics.total_return === "number" ? run.metrics.total_return : null)}</TableCell>
                    <TableCell>
                      <Badge className="border-white/10 bg-white/8 text-zinc-200">{String(run.metrics.notes ?? "—")}</Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
