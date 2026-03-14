import Link from "next/link";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { SectionHeading } from "@/components/section-heading";
import { getIndicators } from "@/lib/data";

export default function IndicatorsPage() {
  const indicators = getIndicators();

  return (
    <div className="space-y-6">
      <SectionHeading
        eyebrow="Indicators"
        title="Catalog"
        body="Every indicator keeps its provenance, classification, readiness state, and run coverage in one place."
      />

      <Card className="glass rounded-[2rem] text-white">
        <CardHeader>
          <CardTitle className="text-lg">Indicator inventory</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow className="border-white/10 hover:bg-transparent">
                <TableHead className="text-zinc-400">Indicator</TableHead>
                <TableHead className="text-zinc-400">Classification</TableHead>
                <TableHead className="text-zinc-400">Status</TableHead>
                <TableHead className="text-zinc-400">Coverage</TableHead>
                <TableHead className="text-zinc-400">Source</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {indicators.length === 0 ? (
                <TableRow className="border-white/10 hover:bg-transparent">
                  <TableCell colSpan={5} className="py-10 text-center text-zinc-400">
                    No indicators yet. Ingest one, then run `tvir export-frontend`.
                  </TableCell>
                </TableRow>
              ) : (
                indicators.map((indicator) => (
                  <TableRow key={indicator.slug} className="border-white/10 hover:bg-white/4">
                    <TableCell>
                      <div>
                        <Link href={`/indicators/${indicator.slug}`} className="font-medium text-white hover:text-cyan-300">
                          {indicator.title}
                        </Link>
                        <p className="text-sm text-zinc-400">{indicator.author}</p>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge className="border-cyan-300/20 bg-cyan-400/10 text-cyan-100">
                        {indicator.classification}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <Badge className="border-emerald-300/20 bg-emerald-400/10 text-emerald-100">
                        {indicator.status}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-zinc-300">
                      {indicator.coverage.runCount} run(s)
                      <div className="text-xs text-zinc-500">
                        {indicator.coverage.pairs.join(", ") || "No pairs"} · {indicator.coverage.timeframes.join(", ") || "No TFs"}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm text-zinc-400">{indicator.discoveredFrom || "—"}</TableCell>
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
