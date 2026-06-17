"""Database models for gepricing backend."""

from .approval_log import ApprovalLog, ApprovalLogCreate, ApprovalLogRead
from .applied_price_change import (
    AppliedPriceChange,
    AppliedPriceChangeCreate,
    AppliedPriceChangeRead,
)
from .category import Category, CategoryCreate, CategoryRead
from .competitor_listing import (
    CompetitorListing,
    CompetitorListingCreate,
    CompetitorListingRead,
)
from .competitor_price import (
    CompetitorPrice,
    CompetitorPriceCreate,
    CompetitorPriceRead,
)
from .competitor_source import (
    CompetitorSource,
    CompetitorSourceCreate,
    CompetitorSourceRead,
)
from .crawler_run import CrawlerRun, CrawlerRunCreate, CrawlerRunRead, CrawlerRunUpdate
from .inventory_snapshot import (
    InventorySnapshot,
    InventorySnapshotCreate,
    InventorySnapshotRead,
)
from .market_alert import MarketAlert, MarketAlertCreate, MarketAlertRead
from .price_comparison import PriceComparison, PriceComparisonCreate, PriceComparisonRead
from .price_recommendation import (
    PriceRecommendation,
    PriceRecommendationCreate,
    PriceRecommendationRead,
    PriceRecommendationUpdate,
)
from .recommendation_event import (
    RecommendationEvent,
    RecommendationEventCreate,
    RecommendationEventRead,
)
from .sales_metrics_hourly import (
    SalesMetricsHourly,
    SalesMetricsHourlyCreate,
    SalesMetricsHourlyRead,
)
from .sku import SKU, SKUCreate, SKURead, SKUUpdate
from .strategy import Strategy, StrategyCreate, StrategyRead, StrategyUpdate
from .strategy_rule import (
    StrategyRule,
    StrategyRuleCreate,
    StrategyRuleRead,
    StrategyRuleUpdate,
)
from .strategy_run import StrategyRun, StrategyRunCreate, StrategyRunRead, StrategyRunUpdate
from .ui_change_feed import UIChangeFeed, UIChangeFeedCreate, UIChangeFeedRead

__all__ = [
    # Categories
    "Category",
    "CategoryCreate",
    "CategoryRead",
    # SKU
    "SKU",
    "SKUCreate",
    "SKURead",
    "SKUUpdate",
    # Competitor Sources
    "CompetitorSource",
    "CompetitorSourceCreate",
    "CompetitorSourceRead",
    # Strategies
    "Strategy",
    "StrategyCreate",
    "StrategyRead",
    "StrategyUpdate",
    # Strategy Rules
    "StrategyRule",
    "StrategyRuleCreate",
    "StrategyRuleRead",
    "StrategyRuleUpdate",
    # Competitor Listings
    "CompetitorListing",
    "CompetitorListingCreate",
    "CompetitorListingRead",
    # Crawler Runs
    "CrawlerRun",
    "CrawlerRunCreate",
    "CrawlerRunRead",
    "CrawlerRunUpdate",
    # Competitor Prices
    "CompetitorPrice",
    "CompetitorPriceCreate",
    "CompetitorPriceRead",
    # Inventory Snapshots
    "InventorySnapshot",
    "InventorySnapshotCreate",
    "InventorySnapshotRead",
    # Sales Metrics
    "SalesMetricsHourly",
    "SalesMetricsHourlyCreate",
    "SalesMetricsHourlyRead",
    # Strategy Runs
    "StrategyRun",
    "StrategyRunCreate",
    "StrategyRunRead",
    "StrategyRunUpdate",
    # Price Recommendations
    "PriceRecommendation",
    "PriceRecommendationCreate",
    "PriceRecommendationRead",
    "PriceRecommendationUpdate",
    # Approval Logs
    "ApprovalLog",
    "ApprovalLogCreate",
    "ApprovalLogRead",
    # Recommendation Events
    "RecommendationEvent",
    "RecommendationEventCreate",
    "RecommendationEventRead",
    # Applied Price Changes
    "AppliedPriceChange",
    "AppliedPriceChangeCreate",
    "AppliedPriceChangeRead",
    # Market Alerts
    "MarketAlert",
    "MarketAlertCreate",
    "MarketAlertRead",
    # Price Comparisons
    "PriceComparison",
    "PriceComparisonCreate",
    "PriceComparisonRead",
    # UI Change Feed
    "UIChangeFeed",
    "UIChangeFeedCreate",
    "UIChangeFeedRead",
]
