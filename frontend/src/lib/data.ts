import coverage from "@/generated/coverage-matrix.json";
import dashboard from "@/generated/dashboard-summary.json";
import indicators from "@/generated/indicators-index.json";
import rankings from "@/generated/rankings-index.json";
import runs from "@/generated/runs-index.json";

export type IndicatorRecord = {
  slug: string;
  title: string;
  author: string;
  classification: string;
  status: string;
  repaintRisk: string;
  discoveredFrom: string;
  pineVersion: string;
  scriptType: string;
  sourceUrl: string;
  tags: string[];
  notes: string;
  analysis: {
    summary: string;
    signalModel: string;
    cautionFlags: string[];
    translationNotes: string;
  };
  coverage: {
    runCount: number;
    pairs: string[];
    timeframes: string[];
  };
};

export type RunRecord = {
  runId: string;
  indicatorSlug: string;
  exchange: string;
  pair: string;
  timeframe: string;
  dateRange: { start?: string; end?: string };
  feesBps?: number;
  slippageBps?: number;
  metrics: Record<string, string | number | null>;
  summary: string;
};

export type RankingRecord = {
  indicatorSlug: string;
  runId: string;
  totalReturn: number | null;
  maxDrawdown: number | null;
  sharpeRatio: number | null;
  winRate: number | null;
  tradeCount: number | null;
  notes: string;
};

export function getDashboard() {
  return dashboard;
}

export function getIndicators(): IndicatorRecord[] {
  return indicators.items as IndicatorRecord[];
}

export function getIndicator(slug: string): IndicatorRecord | undefined {
  return getIndicators().find((indicator) => indicator.slug === slug);
}

export function getRuns(): RunRecord[] {
  return runs.items as RunRecord[];
}

export function getRun(runId: string): RunRecord | undefined {
  return getRuns().find((run) => run.runId === runId);
}

export function getIndicatorRuns(slug: string): RunRecord[] {
  return getRuns().filter((run) => run.indicatorSlug === slug);
}

export function getRankings(): { items: RankingRecord[]; failed: Array<Record<string, string>> } {
  return rankings as { items: RankingRecord[]; failed: Array<Record<string, string>> };
}

export function getCoverage() {
  return coverage as {
    pairs: string[];
    timeframes: string[];
    cells: Array<{
      indicatorSlug: string;
      indicatorTitle: string;
      pair: string;
      timeframe: string;
      status: string;
      runId: string | null;
      totalReturn: number | null;
    }>;
  };
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}
