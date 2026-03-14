import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table";
import { SectionHeading } from "@/components/section-heading";
import { getCoverage, formatPercent } from "@/lib/data";

export default function CoveragePage() {
  const coverage = getCoverage();

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Coverage"
        title="Pair × timeframe test matrix"
        body="This is the fast way to see what has actually been tested versus what only exists as theory or catalog metadata."
      />

      <Card className="glass rounded-[2rem] text-white">
        <CardHeader>
          <CardTitle className="text-lg">Coverage cells</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-white/10 hover:bg-transparent">
                <TableHead className="text-zinc-400">Indicator</TableHead>
                <TableHead className="text-zinc-400">Pair</TableHead>
                <TableHead className="text-zinc-400">Timeframe</TableHead>
                <TableHead className="text-zinc-400">Status</TableHead>
                <TableHead className="text-zinc-400">Latest</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {coverage.cells.length === 0 ? (
                <TableRow className="border-white/10 hover:bg-transparent">
                  <TableCell colSpan={5} className="py-10 text-center text-zinc-400">
                    No coverage yet. Run at least one benchmark and export the frontend indexes.
                  </TableCell>
                </TableRow>
              ) : (
                coverage.cells.map((cell) => (
                  <TableRow key={`${cell.indicatorSlug}-${cell.pair}-${cell.timeframe}`} className="border-white/10 hover:bg-white/4">
                    <TableCell>
                      <Link href={`/indicators/${cell.indicatorSlug}`} className="font-medium text-white hover:text-cyan-300">
                        {cell.indicatorTitle}
                      </Link>
                    </TableCell>
                    <TableCell className="text-zinc-300">{cell.pair || "—"}</TableCell>
                    <TableCell className="text-zinc-300">{cell.timeframe || "—"}</TableCell>
                    <TableCell>
                      <Badge className="border-white/10 bg-white/8 text-zinc-200">{cell.status}</Badge>
                    </TableCell>
                    <TableCell className="text-zinc-300">
                      {cell.runId ? (
                        <Link href={`/runs/${cell.runId}`} className="text-cyan-300 hover:text-cyan-200">
                          {formatPercent(cell.totalReturn)}
                        </Link>
                      ) : (
                        "—"
                      )}
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
