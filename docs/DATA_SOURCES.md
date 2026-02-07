# Options Data Sources Research

> **Research Date:** January 2026
> **Purpose:** Identify EOD historical options data sources for Wheel Strategy backtesting
> **Requirements:** Historical options chains with Greeks (especially delta), SPY + expandable to other tickers

---

## Executive Summary

| Recommendation | Source | Cost | Tickers | Greeks | History |
|----------------|--------|------|---------|--------|---------|
| **Primary (Start Here)** | philippdubach/options-data | FREE | 104 | ✅ Full | 2008+ |
| **Future Expansion** | EODHD API | $19.99+/mo | 6,000+ | ✅ Full | 2018+ |
| **Premium Analytics** | ORATS | $99+/mo | 5,000+ | ✅ Full + Smoothed | 2007+ |
| **Alternative Paid** | Polygon.io / Massive | $29+/mo | All | ✅ Full | 2004+ |

---

## Selected Primary Source: philippdubach/options-data

### Overview

| Attribute | Value |
|-----------|-------|
| **Repository** | https://github.com/philippdubach/options-data |
| **Author** | Philipp Dubach ([philippdubach.com](https://philippdubach.com)) |
| **License** | MIT |
| **Cost** | FREE |
| **Last Updated** | December 2025 |
| **Stars** | 8 (as of Jan 2026) |

### Data Coverage

| Attribute | Value |
|-----------|-------|
| **Date Range** | January 2, 2008 - December 16, 2025 |
| **Tickers** | 104 major US equities and ETFs |
| **Data Points** | 53+ million option contracts |
| **Format** | Parquet files |
| **Hosting** | Cloudflare R2 (fast, reliable CDN) |

### Available Tickers (Complete List)

All 104 tickers available in the philippdubach dataset, organized by sector:

#### ETFs (4)
SPY, QQQ, IWM, VIX

#### Technology (23)
AAPL, ADBE, AMD, AMZN, AVGO, CRM, CSCO, GOOG, GOOGL, IBM, INTU, META, MSFT, NFLX, NOW, NVDA, ORCL, PLTR, PYPL, QCOM, TSLA, TXN, UBER

#### Financials (17)
AIG, AXP, BAC, BK, BLK, BRK.B, C, COF, GS, JPM, MA, MET, MS, SCHW, USB, V, WFC

#### Healthcare & Pharma (14)
ABBV, ABT, BMY, CVS, GILD, ISRG, JNJ, LLY, MDT, MRK, PFE, TMO, UNH, AMGN

#### Consumer (16)
CL, COST, DIS, HD, KO, LOW, MCD, MDLZ, MO, NKE, PEP, PG, PM, SBUX, TGT, WMT

#### Industrials (14)
BA, CAT, DE, DHR, EMR, FDX, GD, GE, HON, LMT, MMM, RTX, UNP, UPS

#### Energy (3)
COP, CVX, XOM

#### Communication Services (4)
CMCSA, T, TMUS, VZ

#### Utilities (3)
DUK, NEE, SO

#### Real Estate (2)
AMT, SPG

#### Materials (1)
LIN

#### Business Services (1)
ACN

**Total: 104 tickers** covering major US equities and ETFs with liquid options markets

### Data Fields

```
Options Data:
├── symbol              # Underlying ticker
├── expiration          # Option expiration date
├── strike              # Strike price
├── option_type         # 'call' or 'put'
├── bid                 # Bid price
├── ask                 # Ask price
├── last                # Last trade price
├── volume              # Daily volume
├── open_interest       # Open interest
├── implied_volatility  # IV
├── delta               # Delta greek
├── gamma               # Gamma greek
├── theta               # Theta greek
├── vega                # Vega greek
├── rho                 # Rho greek
└── underlying_price    # Underlying spot price

Underlying Data:
├── date
├── open
├── high
├── low
├── close
├── adj_close
├── volume
└── dividends
```

### How to Access

```python
import pandas as pd

# Direct download URLs
BASE_URL = "https://static.philippdubach.com/data/options"

# Download SPY options for 2024
spy_2024 = pd.read_parquet(f"{BASE_URL}/spy/options/2024.parquet")

# Download SPY underlying prices
spy_underlying = pd.read_parquet(f"{BASE_URL}/spy/underlying.parquet")

# Available years: 2008-2025
```

### Safety Assessment

| Factor | Assessment |
|--------|------------|
| **License** | ✅ MIT - fully permissive for any use |
| **Data Source** | ⚠️ "Sourced from public market data" - exact source not specified |
| **Author** | ✅ Active developer with technical blog, multiple open-source projects |
| **Maintenance** | ✅ Recently updated (Dec 2025), actively maintained |
| **Institutional Use** | ⚠️ No known institutional endorsements |
| **Validation** | ⚠️ No third-party verification found |

**Recommendation:** Safe for development and research. For production trading, cross-validate sample data against broker historical data or a paid source.

### Limitations

1. **Fixed ticker list** - Cannot request arbitrary new tickers
2. **Update frequency** - Depends on maintainer (not real-time)
3. **No SLA** - Free resource with no guarantees
4. **Unverified accuracy** - No third-party audit of data quality

---

## Paid Alternatives for Future Expansion

### ORATS (Premium Analytics)

| Attribute | Value |
|-----------|-------|
| **Website** | https://orats.com |
| **Pricing** | $99/mo (Delayed) / $199/mo (Live) / $399/mo (Intraday) |
| **One-Time Historical** | $599 for complete 2007-present dataset |
| **Tickers** | 5,000+ US equities and ETFs |
| **History** | 2007 - present (EOD), Aug 2020+ (intraday) |
| **Greeks** | ✅ Full Greeks + Smoothed Market Values (proprietary) |
| **IV** | ✅ Implied volatility + IV surfaces |
| **Special Features** | Theoretical values, 500+ proprietary indicators |
| **Backtesting** | ✅ Built-in backtesting API for 25 strategies |
| **Rate Limits** | 20k/mo (Delayed), 100k/mo (Live), 1M/mo (Intraday) |

**Pros:**
- Longest history (2007+) among API providers
- "Smoothed Market Values" - proprietary cleaned Greeks (more stable than raw)
- Built-in backtesting engine for options strategies
- Data captured 14 min before close (avoids wide EOD spreads)
- 500+ proprietary indicators beyond standard Greeks
- One-time $599 purchase option for full historical dataset
- Powers Tradier's Greeks data (industry trusted)

**Cons:**
- More expensive than EODHD ($99 vs $20/mo)
- No free tier
- S3 storage costs ($1-2k) for bulk historical downloads
- May be overkill for simple wheel strategy

**Best For:** Serious options traders needing premium analytics, volatility research, or complex multi-leg strategies.

---

### EODHD (Recommended for Expansion)

| Attribute | Value |
|-----------|-------|
| **Website** | https://eodhd.com |
| **Pricing** | $19.99/mo (Basic) - $99.99/mo (All-in-One) |
| **Tickers** | 6,000+ US stocks with options |
| **History** | April 2018 - present |
| **Greeks** | ✅ Delta, Gamma, Theta, Vega |
| **IV** | ✅ Implied volatility included |
| **API** | REST API, JSON format |
| **Rate Limits** | 100,000 requests/day (paid plans) |

**Pros:**
- Best value for many tickers ($19.99/mo for 6,000+ symbols)
- Full Greeks included
- Good documentation and Python SDK
- Student/academic discount (50% off)

**Cons:**
- History starts 2018 (shorter than philippdubach)
- API-based (requires network calls)

### Polygon.io / Massive

| Attribute | Value |
|-----------|-------|
| **Website** | https://polygon.io |
| **Pricing** | $29/mo (Starter) - $199/mo (Advanced) |
| **Tickers** | All optionable US securities |
| **History** | 2004+ |
| **Greeks** | ✅ On higher tiers |
| **Format** | REST API + Flat file downloads |

**Pros:**
- Longest history available
- High-quality institutional-grade data
- Flat file bulk downloads included
- Excellent API design

**Cons:**
- More expensive
- Options require higher tiers

### Theta Data

| Attribute | Value |
|-----------|-------|
| **Website** | https://thetadata.net |
| **Pricing** | Free (limited) / $25+/mo (Value tier for Greeks) |
| **Tickers** | All optionable US securities |
| **History** | 2012+ (UTP tape), 2020+ (CTA tape) |
| **Free Tier** | EOD prices only, NO Greeks |
| **Greeks** | ✅ On paid tiers only |

**Pros:**
- Free tier for basic EOD data
- Tick-level data available
- Good for real-time streaming

**Cons:**
- Greeks require paid subscription
- Java terminal required for connection

### CBOE DataShop

| Attribute | Value |
|-----------|-------|
| **Website** | https://datashop.cboe.com |
| **Pricing** | Custom quote (expensive) |
| **Authority** | Primary exchange - most authoritative |
| **History** | 2012+ |
| **Greeks** | ✅ Optional add-on |

**Pros:**
- Official exchange data
- Highest accuracy guarantee
- Full OPRA coverage

**Cons:**
- Expensive (institutional pricing)
- Custom quotes required

### historicaloptiondata.com

| Attribute | Value |
|-----------|-------|
| **Website** | https://historicaloptiondata.com |
| **Pricing** | ~$50-200 one-time purchase |
| **History** | 2005-present |
| **Greeks** | ✅ Full Greeks + IV |
| **Format** | CSV/SQL files |

**Pros:**
- One-time purchase (no subscription)
- Long history
- Used by MIT, Stanford, 300+ institutions

**Cons:**
- Manual download process
- May need updates for recent data

---

## Free Sources (Limited Use)

### Tradier API

| Attribute | Value |
|-----------|-------|
| **Website** | https://tradier.com |
| **Cost** | Free sandbox account |
| **Greeks** | ✅ Via ORATS partnership (same quality as ORATS $99/mo tier) |
| **Limitation** | Current/recent data only - NO deep historical |
| **Rate Limit** | 60 req/min (sandbox), 120 req/min (production) |

**Verdict:** Good for live trading integration, NOT for historical backtesting. Note: Greeks quality is excellent (powered by ORATS) but only for current data.

### yfinance (Yahoo Finance)

| Attribute | Value |
|-----------|-------|
| **Cost** | Free |
| **Greeks** | ❌ Only IV, no Greeks |
| **Limitation** | Current chains ONLY - no historical |

**Verdict:** Useful for underlying price data, NOT for historical options.

### Theta Data Free Tier

| Attribute | Value |
|-----------|-------|
| **Cost** | Free |
| **Greeks** | ❌ NOT included in free tier |
| **History** | 1 year EOD only |
| **Rate Limit** | 20-30 req/min |

**Verdict:** Too limited for backtesting without Greeks.

---

## Data Architecture Design

To support switching between data sources, we implement a **provider abstraction layer**:

```
┌─────────────────────────────────────────────────────────────┐
│                   Data Abstraction Layer                    │
│              (OptionsDataProvider interface)                │
└─────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────┬───────┴───────┬─────────────┐
        ▼             ▼               ▼             ▼
┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Philippdubach│ │   EODHD      │ │    ORATS     │ │   Polygon    │
│   Provider   │ │   Provider   │ │   Provider   │ │   Provider   │
│    (FREE)    │ │  ($20/mo)    │ │  ($99/mo)    │ │  ($29+/mo)   │
│   104 tkrs   │ │  6000+ tkrs  │ │  5000+ tkrs  │ │   All tkrs   │
│   2008+      │ │   2018+      │ │   2007+      │ │    2004+     │
└──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘
```

### Provider Interface

```python
from abc import ABC, abstractmethod
from datetime import date
import pandas as pd

class OptionsDataProvider(ABC):
    """Abstract base class for options data providers."""

    @abstractmethod
    def get_options_chain(
        self,
        ticker: str,
        trade_date: date
    ) -> pd.DataFrame:
        """Get full options chain for a ticker on a given date."""
        pass

    @abstractmethod
    def get_underlying_price(
        self,
        ticker: str,
        trade_date: date
    ) -> float:
        """Get underlying closing price."""
        pass

    @abstractmethod
    def get_available_tickers(self) -> list[str]:
        """List all available tickers."""
        pass

    @abstractmethod
    def get_date_range(self, ticker: str) -> tuple[date, date]:
        """Get available date range for a ticker."""
        pass
```

---

## Caching Strategy

All providers use a unified caching layer:

```
cache/
├── raw/                    # Raw data from providers
│   ├── philippdubach/
│   │   ├── spy/
│   │   │   ├── options_2024.parquet
│   │   │   └── underlying.parquet
│   │   └── aapl/
│   └── eodhd/
│       └── spy/
├── computed/               # Derived data (if Greeks computed)
│   └── spy/
│       └── greeks_2024.parquet
└── metadata.json           # Cache index and timestamps
```

**Cache key format:** `{provider}/{ticker}/{data_type}_{year}.parquet`

---

## Validation Checklist

Before using any data source for real trading decisions:

- [ ] Cross-check sample prices against broker historical data
- [ ] Verify Greeks calculations match Black-Scholes model
- [ ] Confirm dividend adjustments are correct
- [ ] Test for data gaps or missing expirations
- [ ] Validate volume/OI against known liquid periods

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| Jan 2026 | Use philippdubach/options-data as primary | Free, full Greeks, 17 years history, 104 tickers |
| Jan 2026 | Design provider abstraction layer | Enable easy switch to EODHD/Polygon later |
| Jan 2026 | Plan EODHD as expansion path | Best price/coverage for 6,000+ tickers |

---

## References

- [philippdubach/options-data](https://github.com/philippdubach/options-data) - Primary free data source
- [ORATS Data API](https://orats.com/data-api) - Premium analytics with smoothed Greeks
- [ORATS Historical EOD Data](https://orats.com/near-eod-data) - One-time $599 dataset purchase
- [ORATS API Documentation](https://docs.orats.io/) - API reference
- [EODHD Options API](https://eodhd.com/lp/us-stock-options-api/) - Recommended paid expansion
- [Polygon.io Options](https://polygon.io/options) - Alternative paid source
- [Theta Data](https://thetadata.net) - Greeks require paid tier
- [CBOE DataShop](https://datashop.cboe.com) - Official exchange data
- [yfinance](https://github.com/ranaroussi/yfinance) - Free underlying data
