import { Badge } from "@/components/ui/badge";

export function ScoreChip({ label, value }: { label: string; value: number | string }) {
  return (
    <Badge className="border-white/10 bg-white/8 px-3 py-1.5 text-zinc-100">
      {label}: {value}
    </Badge>
  );
}
