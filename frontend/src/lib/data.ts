import candidates from "@/generated/candidates-index.json";
import coverage from "@/generated/coverage-matrix.json";
import dashboard from "@/generated/dashboard-summary.json";
import diagnostics from "@/generated/diagnostics-index.json";
import indicators from "@/generated/indicators-index.json";
import experiments from "@/generated/experiments-index.json";
import liveReadiness from "@/generated/live-readiness-index.json";
import rankings from "@/generated/rankings-index.json";
import runtimeOps from "@/generated/runtime-ops.json";
import runtimeSignals from "@/generated/runtime-signals.json";
import runs from "@/generated/runs-index.json";

export type CandidateAssessment = {
  indicatorSlug: string;
  overallScore: number;
  confidenceScore: number;
  robustnessScore: number;
  liveReadinessScore: number;
  verdict: string;
  reasonCodes: string[];
  strengths: string[];
  weaknesses: string[];
  failureModes: string[];
  killCriteria: string[];
  recommendedNextStep: string;
  runCount: number;
  pairs: string[];
  timeframes: string[];
  latestRunId: string | null;
};

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
  assessment?: CandidateAssessment;
};

export type ExperimentRecord = {
  experimentSlug: string;
  title: string;
  family: string;
  variant: string;
  kind: string;
  status: string;
  indicators: string[];
  tags: string[];
  params: Record<string, unknown>;
  filters: string[];
  exits: string[];
  matrix: string;
  horizons: string[];
  notes: string;
  rationale: string;
  runCount: number;
  latestRunId?: string | null;
  latestMetrics?: Record<string, string | number | boolean | null> | null;
};

export type RunRecord = {
  runId: string;
  indicatorSlug: string;
  experimentSlug?: string | null;
  experimentFamily?: string | null;
  experimentVariant?: string | null;
  exchange: string;
  pair: string;
  timeframe: string;
  dateRange: { start?: string; end?: string };
  actualRange?: { start?: string; end?: string };
  barCount?: number | null;
  coverageStatus?: string;
  coverageComplete?: boolean | null;
  coverageGapDays?: number | null;
  feesBps?: number;
  slippageBps?: number;
  engine?: string;
  metrics: Record<string, string | number | boolean | null>;
  summary: string;
};

export type RankingRecord = {
  indicatorSlug: string;
  experimentSlug?: string;
  experimentFamily?: string;
  experimentVariant?: string;
  experimentKind?: string;
  runId: string;
  exchange?: string;
  pair?: string;
  timeframe?: string;
  engine?: string;
  configuredStart?: string;
  configuredEnd?: string;
  actualStart?: string;
  actualEnd?: string;
  barCount?: number | null;
  coverageStatus?: string;
  coverageComplete?: boolean | null;
  coverageGapDays?: number | null;
  feesBps?: number | null;
  slippageBps?: number | null;
  entrySignalCount?: number | null;
  exitSignalCount?: number | null;
  totalReturn: number | null;
  maxDrawdown: number | null;
  sharpeRatio: number | null;
  winRate: number | null;
  tradeCount: number | null;
  notes: string;
};

export type RuntimeSignalRecord = {
  id: string;
  signal_at: string;
  strategy_slug: string;
  strategy_title?: string | null;
  venue: string;
  symbol: string;
  timeframe: string;
  signal_type: string;
  signal_source: string;
  price?: number | null;
  dedupe_key: string;
  context: Record<string, unknown>;
  strategy_version: string;
};

export type RuntimeOpsRecord = {
  worker_name: string;
  lane: string;
  status: string;
  heartbeat_at: string;
  lag_seconds?: number | null;
  error_summary?: string | null;
  tracked_feeds: number;
};

export type PromotedStrategyRecord = {
  slug: string;
  title?: string | null;
  version: string;
  stage: string;
  runtime_enabled: boolean;
  paper_enabled: boolean;
  latest_verdict?: string | null;
  latest_rationale?: string | null;
  decided_at?: string | null;
  pair?: string | null;
  timeframe?: string | null;
  total_return?: number | null;
  max_drawdown?: number | null;
  sharpe_ratio?: number | null;
  trade_count?: number | null;
  coverage_status?: string | null;
};

export type RuntimeSnapshot<T> = {
  status: string;
  generatedAt: string;
  error?: string;
  items: T[];
  promotedStrategies: PromotedStrategyRecord[];
};

export function getDashboard() {
  return dashboard as {
    totals: Record<string, number>;
    statusCounts: Record<string, number>;
    classificationCounts: Record<string, number>;
    verdictCounts: Record<string, number>;
    topRanked: RankingRecord[];
    topCandidates: CandidateAssessment[];
    recentRuns: RunRecord[];
  };
}

export function getIndicators(): IndicatorRecord[] {
  return indicators.items as IndicatorRecord[];
}

export function getExperiments(): ExperimentRecord[] {
  return experiments.items as ExperimentRecord[];
}

export function getExperiment(slug: string): ExperimentRecord | undefined {
  return getExperiments().find((experiment) => experiment.experimentSlug === slug);
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

export function getExperimentRuns(slug: string): RunRecord[] {
  return getRuns().filter((run) => run.experimentSlug === slug);
}

export function getIndicatorRuns(slug: string): RunRecord[] {
  return getRuns().filter((run) => run.indicatorSlug === slug);
}

export function getRankings(): { items: RankingRecord[]; history?: RankingRecord[]; failed: Array<Record<string, string>> } {
  return rankings as { items: RankingRecord[]; history?: RankingRecord[]; failed: Array<Record<string, string>> };
}

export function getCandidates(): CandidateAssessment[] {
  return candidates.items as CandidateAssessment[];
}

export function getCandidate(slug: string): CandidateAssessment | undefined {
  return getCandidates().find((item) => item.indicatorSlug === slug);
}

export function getDiagnostics() {
  return diagnostics as {
    items: Array<{
      indicatorSlug: string;
      verdict: string;
      weaknesses: string[];
      failureModes: string[];
      killCriteria: string[];
      reasonCodes: string[];
    }>;
  };
}

export function getLiveReadiness() {
  return liveReadiness as {
    items: Array<{
      indicatorSlug: string;
      liveReadinessScore: number;
      verdict: string;
      nextStage: string;
      blockers: string[];
      recommendedNextStep: string;
    }>;
  };
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

export function getRuntimeSignals(): RuntimeSnapshot<RuntimeSignalRecord> {
  return runtimeSignals as RuntimeSnapshot<RuntimeSignalRecord>;
}

export function getRuntimeOps(): RuntimeSnapshot<RuntimeOpsRecord> {
  return runtimeOps as RuntimeSnapshot<RuntimeOpsRecord>;
}

export function formatPercent(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function formatNumber(value: number | null | undefined) {
  if (value === null || value === undefined || Number.isNaN(value)) return "—";
  return value.toFixed(2);
}

export function verdictTone(verdict: string) {
  if (verdict.includes("paper") || verdict.includes("live")) return "emerald";
  if (verdict.includes("keep")) return "amber";
  return "zinc";
}
