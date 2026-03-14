from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class RuntimeDatabaseConfig:
    provider: str
    url_env: str
    pooled_url_env: str | None = None


@dataclass(slots=True)
class RuntimeSourceOfTruth:
    research_artifacts: str
    operational_state: str


@dataclass(slots=True)
class RuntimeModeConfig:
    paper_trading_enabled: bool = True
    live_execution_enabled: bool = False
    source_of_truth: RuntimeSourceOfTruth = field(
        default_factory=lambda: RuntimeSourceOfTruth(
            research_artifacts="results/",
            operational_state="neon",
        )
    )


@dataclass(slots=True)
class RuntimeStrategyConfig:
    slug: str
    version: str
    enabled: bool = True
    minimum_candles: int = 200
    watchlist_keys: list[str] = field(default_factory=list)
    signal_columns: dict[str, str] = field(
        default_factory=lambda: {
            "entry_long": "entry",
            "exit_long": "exit",
            "entry_short": "entry_short",
            "exit_short": "exit_short",
            "flat": "flat",
        }
    )

    def __post_init__(self) -> None:
        if not self.slug.strip():
            raise ValueError("strategies[].slug must not be empty")
        if not self.version.strip():
            raise ValueError("strategies[].version must not be empty")
        _require_positive_int(self.minimum_candles, "strategies[].minimum_candles")
        if not self.signal_columns:
            raise ValueError("strategies[].signal_columns must include at least one signal mapping")

    @property
    def identity_key(self) -> str:
        return f"{self.slug}@{self.version}"

    def applies_to(self, watchlist_key: str) -> bool:
        return not self.watchlist_keys or watchlist_key in self.watchlist_keys


@dataclass(slots=True)
class WatchlistEntry:
    venue: str
    symbol: str
    timeframe: str

    @property
    def key(self) -> str:
        return f"{self.venue}:{self.symbol}:{self.timeframe}"


@dataclass(slots=True)
class WatchlistConfig:
    exchange: str
    symbols: list[str]
    timeframes: list[str]

    def __post_init__(self) -> None:
        if not self.exchange.strip():
            raise ValueError("watchlist.exchange must not be empty")
        if not self.symbols:
            raise ValueError("watchlist.symbols must include at least one symbol")
        if not self.timeframes:
            raise ValueError("watchlist.timeframes must include at least one timeframe")

    def expand(self) -> list[WatchlistEntry]:
        return [
            WatchlistEntry(venue=self.exchange, symbol=symbol, timeframe=timeframe)
            for symbol in self.symbols
            for timeframe in self.timeframes
        ]


@dataclass(slots=True)
class MarketDataCadenceConfig:
    poll_seconds: int = 60
    align_to_candle_close: bool = True
    write_on_new_candle_only: bool = True
    lag_tolerance_seconds: int = 15

    def __post_init__(self) -> None:
        _require_positive_int(self.poll_seconds, "market_data.cadence.poll_seconds")
        _require_non_negative_int(
            self.lag_tolerance_seconds,
            "market_data.cadence.lag_tolerance_seconds",
        )


@dataclass(slots=True)
class SignalCadenceConfig:
    poll_seconds: int = 60
    align_to_candle_close: bool = True
    evaluate_on_new_candle_only: bool = True
    lag_tolerance_seconds: int = 15

    def __post_init__(self) -> None:
        _require_positive_int(self.poll_seconds, "signals.cadence.poll_seconds")
        _require_non_negative_int(
            self.lag_tolerance_seconds,
            "signals.cadence.lag_tolerance_seconds",
        )


@dataclass(slots=True)
class SignalBatchingConfig:
    emit_on_state_change_only: bool = True
    dedupe_window_seconds: int = 21_600
    flush_interval_seconds: int = 30
    max_batch_size: int = 25

    def __post_init__(self) -> None:
        _require_positive_int(
            self.dedupe_window_seconds,
            "signals.batching.dedupe_window_seconds",
        )
        _require_positive_int(
            self.flush_interval_seconds,
            "signals.batching.flush_interval_seconds",
        )
        _require_positive_int(self.max_batch_size, "signals.batching.max_batch_size")


@dataclass(slots=True)
class MarketDataWorkerConfig:
    enabled: bool = True
    worker_name: str = "market_data"
    fetch_limit: int = 250
    cadence: MarketDataCadenceConfig = field(default_factory=MarketDataCadenceConfig)

    def __post_init__(self) -> None:
        if not self.worker_name.strip():
            raise ValueError("market_data.worker_name must not be empty")
        _require_positive_int(self.fetch_limit, "market_data.fetch_limit")


@dataclass(slots=True)
class SignalWorkerConfig:
    enabled: bool = True
    worker_name: str = "signals"
    primary_source: str = "local_evaluator"
    optional_adapters: list[str] = field(default_factory=list)
    candle_limit: int = 250
    cadence: SignalCadenceConfig = field(default_factory=SignalCadenceConfig)
    batching: SignalBatchingConfig = field(default_factory=SignalBatchingConfig)

    def __post_init__(self) -> None:
        if not self.worker_name.strip():
            raise ValueError("signals.worker_name must not be empty")
        _require_positive_int(self.candle_limit, "signals.candle_limit")


@dataclass(slots=True)
class PaperWorkerConfig:
    enabled: bool = True
    worker_name: str = "paper"
    starting_equity: float = 100_000.0
    max_open_positions: int = 5
    flush_interval_seconds: int = 60

    def __post_init__(self) -> None:
        if not self.worker_name.strip():
            raise ValueError("paper.worker_name must not be empty")
        if self.starting_equity <= 0:
            raise ValueError("paper.starting_equity must be greater than 0")
        _require_positive_int(self.max_open_positions, "paper.max_open_positions")
        _require_positive_int(self.flush_interval_seconds, "paper.flush_interval_seconds")


@dataclass(slots=True)
class OpsHeartbeatConfig:
    collect_seconds: int = 30
    flush_interval_seconds: int = 120
    max_batch_size: int = 20
    include_stats: bool = True

    def __post_init__(self) -> None:
        _require_positive_int(self.collect_seconds, "ops.heartbeat.collect_seconds")
        _require_positive_int(self.flush_interval_seconds, "ops.heartbeat.flush_interval_seconds")
        _require_positive_int(self.max_batch_size, "ops.heartbeat.max_batch_size")


@dataclass(slots=True)
class OpsWorkerConfig:
    enabled: bool = True
    worker_name: str = "ops"
    heartbeat: OpsHeartbeatConfig = field(default_factory=OpsHeartbeatConfig)

    def __post_init__(self) -> None:
        if not self.worker_name.strip():
            raise ValueError("ops.worker_name must not be empty")


@dataclass(slots=True)
class RuntimeWorkersConfig:
    market_data: MarketDataWorkerConfig = field(default_factory=MarketDataWorkerConfig)
    signals: SignalWorkerConfig = field(default_factory=SignalWorkerConfig)
    paper: PaperWorkerConfig = field(default_factory=PaperWorkerConfig)
    ops: OpsWorkerConfig = field(default_factory=OpsWorkerConfig)


@dataclass(slots=True)
class ResearchAlignmentConfig:
    required_backtest_fields: list[str] = field(default_factory=list)


@dataclass(slots=True)
class RuntimeConfig:
    environment: str
    database: RuntimeDatabaseConfig
    runtime: RuntimeModeConfig
    watchlist: WatchlistConfig
    workers: RuntimeWorkersConfig
    strategies: list[RuntimeStrategyConfig] = field(default_factory=list)
    research_alignment: ResearchAlignmentConfig = field(default_factory=ResearchAlignmentConfig)

    def watchlist_entries(self) -> list[WatchlistEntry]:
        return self.watchlist.expand()

    def enabled_strategies(self) -> list[RuntimeStrategyConfig]:
        return [strategy for strategy in self.strategies if strategy.enabled]


@dataclass(slots=True)
class MarketDataPollDecision:
    due: bool
    reason: str
    next_poll_at: datetime
    candle_close_at: datetime | None = None


@dataclass(slots=True)
class SignalEventCandidate:
    strategy_slug: str
    strategy_version: str
    venue: str
    symbol: str
    timeframe: str
    signal_type: str
    signal_at: datetime
    candle_close_at: datetime
    signal_source: str = "local_evaluator"
    state: str | None = None
    price: float | None = None
    candle_open_at: datetime | None = None
    context: dict[str, Any] = field(default_factory=dict)

    @property
    def watchlist_key(self) -> str:
        return f"{self.venue}:{self.symbol}:{self.timeframe}"

    @property
    def strategy_identity(self) -> str:
        return f"{self.strategy_slug}@{self.strategy_version}"

    @property
    def identity_key(self) -> str:
        return f"{self.strategy_identity}:{self.watchlist_key}"


@dataclass(slots=True)
class WorkerHeartbeatSample:
    worker_name: str
    lane: str
    status: str
    heartbeat_at: datetime
    lag_seconds: int | None = None
    stats: dict[str, Any] = field(default_factory=dict)
    error_summary: str | None = None


@dataclass(slots=True)
class MarketDataWorkerRunResult:
    due_watchlists: int
    refreshed_watchlists: int
    latest_candle_close_at_by_watchlist: dict[str, datetime]
    heartbeat_rows_written: int


@dataclass(slots=True)
class SignalWorkerRunResult:
    due_watchlists: int
    evaluated_watchlists: int
    accepted_events: int
    persisted_events: int
    pending_events: int
    heartbeat_rows_written: int


@dataclass(slots=True)
class OpsWorkerRunResult:
    pending_heartbeats: int
    heartbeat_rows_written: int


def _require_positive_int(value: int, label: str) -> None:
    if value <= 0:
        raise ValueError(f"{label} must be greater than 0")


def _require_non_negative_int(value: int, label: str) -> None:
    if value < 0:
        raise ValueError(f"{label} must be zero or greater")
