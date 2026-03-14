import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

export function MetricCard({
  label,
  value,
  hint,
}: {
  label: string;
  value: string | number;
  hint: string;
}) {
  return (
    <Card className="border-white/10 bg-white/6 text-white shadow-[0_20px_80px_-30px_rgba(0,255,214,0.18)] backdrop-blur-xl">
      <CardHeader className="pb-3">
        <CardTitle className="text-xs uppercase tracking-[0.35em] text-zinc-400">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-semibold tracking-tight">{value}</div>
        <p className="mt-2 text-sm text-zinc-400">{hint}</p>
      </CardContent>
    </Card>
  );
}
