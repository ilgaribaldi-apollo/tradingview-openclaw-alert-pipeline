export type PromotionVerdict =
  | 'reject'
  | 'keep_researching'
  | 'paper_trade_candidate'
  | 'paper_trading'
  | 'live_candidate'
  | 'live_shadow'
  | 'live_enabled';

export type StrategyStage =
  | 'benchmarked'
  | 'cross_validated'
  | 'paper_trade_candidate'
  | 'paper_trading'
  | 'live_candidate'
  | 'live_shadow'
  | 'live_enabled';

export type WorkerLane = 'market_data' | 'signals' | 'paper' | 'ops';
export type WorkerStatus = 'idle' | 'running' | 'degraded' | 'failed' | 'paused';
export type SignalType = 'entry_long' | 'exit_long' | 'entry_short' | 'exit_short' | 'flat';
export type SignalSource = 'local_evaluator' | 'tradingview_webhook' | 'manual';

export interface BacktestEvidenceSummary {
  exchange?: string;
  symbol?: string;
  timeframe?: string;
  engine?: string;
  configuredStart?: string;
  configuredEnd?: string;
  actualStart?: string;
  actualEnd?: string;
  barCount?: number;
  feesBps?: number;
  slippageBps?: number;
  entrySignalCount?: number;
  exitSignalCount?: number;
  totalReturn?: number;
  maxDrawdown?: number;
  sharpeRatio?: number;
  winRate?: number;
  tradeCount?: number;
  notes?: string;
}

export interface StrategyVersionContract {
  strategySlug: string;
  version: string;
  codePath: string;
  configPath?: string;
  configHash?: string;
  sourceCommit?: string;
  currentStage: StrategyStage;
  runtimeEnabled: boolean;
  paperEnabled: boolean;
  backtestEvidence: BacktestEvidenceSummary;
}

export interface PromotionDecisionContract {
  strategySlug: string;
  strategyVersion: string;
  verdict: PromotionVerdict;
  stageFrom: StrategyStage;
  stageTo: StrategyStage;
  rationale: string;
  reasonCodes: string[];
  strengths: string[];
  weaknesses: string[];
  killCriteria: string[];
  actor: string;
  decidedAt: string;
}

export interface SignalEventContract {
  strategySlug: string;
  strategyVersion: string;
  venue: string;
  symbol: string;
  timeframe: string;
  signalType: SignalType;
  signalSource: SignalSource;
  signalAt: string;
  candleOpenAt?: string;
  candleCloseAt?: string;
  price?: number;
  dedupeKey: string;
  context: Record<string, unknown>;
}

export interface PaperPositionContract {
  id: string;
  strategySlug: string;
  strategyVersion: string;
  venue: string;
  symbol: string;
  timeframe: string;
  side: 'long' | 'short' | 'flat';
  status: 'open' | 'closed' | 'cancelled';
  openedAt: string;
  closedAt?: string;
  entryPrice: number;
  exitPrice?: number;
  quantity: number;
  realizedPnl?: number;
  unrealizedPnl?: number;
}

export interface RuntimeWorkerStatusContract {
  workerName: string;
  lane: WorkerLane;
  status: WorkerStatus;
  heartbeatAt: string;
  lagSeconds?: number;
  errorSummary?: string;
  metadata?: Record<string, unknown>;
}

export interface TradingViewWebhookContract {
  source: 'tradingview';
  strategySlug: string;
  venue: string;
  symbol: string;
  timeframe: string;
  signalType: SignalType;
  signalAt: string;
  price?: number;
  message?: string;
  payloadVersion: 'v1';
}
