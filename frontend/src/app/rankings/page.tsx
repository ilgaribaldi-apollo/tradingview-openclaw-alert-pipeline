import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionHeading } from "@/components/section-heading";
import { formatNumber, formatPercent, getRankings } from "@/lib/data";

export default function RankingsPage() {
  const rankings = getRankings();

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Rankings"
        title="Leaderboard with caveats attached"
        body="If a result looks great but the assumptions are garbage, the UI should say so right next to the number. Experiments now show up as first-class research units, not just hidden notes."
      />

      <Card className="glass rounded-[2rem] text-white">
        <CardHeader>
          <CardTitle className="text-lg">Leaderboard</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-white/10 hover:bg-transparent">
                <TableHead className="text-zinc-400">Indicator / Experiment</TableHead>
                <TableHead className="text-zinc-400">Market</TableHead>
                <TableHead className="text-zinc-400">Return</TableHead>
                <TableHead className="text-zinc-400">Drawdown</TableHead>
                <TableHead className="text-zinc-400">Sharpe</TableHead>
                <TableHead className="text-zinc-400">Trades</TableHead>
                <TableHead className="text-zinc-400">Notes</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rankings.items.length === 0 ? (
                <TableRow className="border-white/10 hover:bg-transparent">
                  <TableCell colSpan={7} className="py-10 text-center text-zinc-400">
                    No rankings yet. Backtest first, then export the frontend indexes.
                  </TableCell>
                </TableRow>
              ) : (
                rankings.items.map((row) => (
                  <TableRow key={row.runId} className="border-white/10 hover:bg-white/4">
                    <TableCell>
                      <div>
                        <Link href={`/runs/${row.runId}`} className="font-medium text-white hover:text-cyan-300">
                          {row.experimentSlug || row.indicatorSlug}
                        </Link>
                        <p className="text-xs text-zinc-500">
                          {row.experimentSlug
                            ? `${row.indicatorSlug} · ${row.experimentFamily || "family?"} · ${row.experimentVariant || "variant?"}`
                            : row.indicatorSlug}
                        </p>
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-zinc-300">
                      {row.pair || "—"} · {row.timeframe || "—"}
                    </TableCell>
                    <TableCell className="text-emerald-300">{formatPercent(row.totalReturn)}</TableCell>
                    <TableCell className="text-rose-300">{formatPercent(row.maxDrawdown)}</TableCell>
                    <TableCell className="text-zinc-300">{formatNumber(row.sharpeRatio)}</TableCell>
                    <TableCell className="text-zinc-300">{row.tradeCount ?? "—"}</TableCell>
                    <TableCell className="max-w-sm text-sm text-zinc-400">{row.notes || "No note recorded."}</TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Card className="glass rounded-[2rem] text-white">
        <CardHeader>
          <CardTitle className="text-lg">Failed runs</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3">
          {rankings.failed.length === 0 ? (
            <p className="text-sm text-zinc-400">No failed runs recorded.</p>
          ) : (
            rankings.failed.map((row, index) => (
              <Badge key={`${row.indicator_slug}-${index}`} className="border-amber-300/20 bg-amber-400/10 px-3 py-1.5 text-amber-100">
                {row.indicator_slug}: {row.error}
              </Badge>
            ))
          )}
        </CardContent>
      </Card>
    </div>
  );
}
