# From Seeded Data to Scraped Data: How I Would Evolve GapSight

This note explains two things:
1. How I would transition this project from seeded/mock data to scraped real-world data.
2. Why I originally chose mock data for this assignment.

---

## Current State (What I Built First)

GapSight currently uses seeded social data to power:
- follower trend charts
- engagement calculations
- competitor benchmarking
- AI-generated strategic insights
- CSV/PDF reports

The dataset is generated once (via a seed script) and stored in Supabase.
That gave me a stable base to build the full product flow quickly and focus on analytics quality.

---

## Why I Started with Mock Data

I made this choice intentionally, not as a shortcut.

### 1) Assignment fit
The task allows real or mocked data. So I prioritized delivering the full dashboard and intelligence flow end-to-end within timeline.

### 2) Product-first execution
The harder part of this assignment is not “just fetching data.”
It is:
- modeling useful metrics,
- comparing against competitors,
- surfacing actionable gaps,
- and presenting insights clearly.

Mock data let me solve those core product problems first.

### 3) Reliability during evaluation
External data integrations can break due rate limits, auth issues, or platform changes.
For an internship evaluation, I wanted predictable behavior for demo and review.

### 4) Clean upgrade path
I designed the backend with feature routers and clear data contracts, so replacing the data source is manageable.
The analytics layer can remain mostly the same while ingestion changes.

---

## Migration Plan: Seeded Data → Scraped Data

## Step 1 — Separate ingestion from analytics
Keep current analytics endpoints, but move data collection into a dedicated ingestion pipeline.

Target split:
- **Ingestion layer**: fetch + parse external profile/post data
- **Storage layer**: raw snapshots and normalized metrics
- **Analytics layer**: existing calculations and insights

This prevents scraping logic from leaking into dashboard endpoints.

## Step 2 — Add source-aware schema fields
Extend current tables (or add staging tables) with metadata such as:
- `source` (scraper/provider)
- `external_profile_id`
- `external_post_id`
- `fetched_at`
- `snapshot_date`
- `ingestion_run_id`

Reason: traceability, dedupe, and easier debugging.

## Step 3 — Build profile & post collectors
For each tracked account (user + competitors), collect:
- follower count over time
- post-level engagement fields
- content type and post timestamps

Store raw values first, then normalized values.

## Step 4 — Schedule incremental sync jobs
Run ingestion periodically (e.g., every 6–24 hours depending on limits).
Use append-only snapshots for time series.

Important: this is near-real-time, not true real-time.

## Step 5 — Add deduplication and idempotency
Use unique keys (for example `external_post_id`) so repeated runs do not duplicate records.

Expected behavior:
- If post exists, update metrics if needed
- If post is new, insert

## Step 6 — Add sync status visibility
Expose freshness and health to frontend:
- `last_synced_at`
- `sync_status` (ok, delayed, failed)
- optional `warning_message`

This improves trust in the dashboard.

## Step 7 — Keep fallback logic for resilience
If scraping fails temporarily:
- continue serving last successful dataset
- surface stale-data indicator
- avoid breaking charts/insights

## Step 8 — Re-tune insights prompts
When using scraped data, include confidence/coverage constraints in insight generation.
Example: if only partial competitor data exists, AI should explicitly state limitations.

---

## Practical Risks and How I’d Handle Them

### Platform policy and compliance risk
Scraping may violate some platform terms depending on method and target.

What I would do:
- use official APIs where possible,
- keep scraping only for permitted public data,
- document constraints clearly.

### Data drift and parser breakage
Page structure can change and break scrapers.

What I would do:
- maintain parser versioning,
- monitor ingestion failures,
- alert on sudden drop in coverage.

### Rate limits and reliability
Aggressive scraping can fail or get blocked.

What I would do:
- queue jobs,
- backoff/retry policy,
- conservative schedule.

---

## What Would Stay the Same in GapSight

Most of the dashboard and analytics logic can remain unchanged because the app already expects structured time-series + engagement fields.

That means migration impact is concentrated in:
- ingestion workers,
- data normalization,
- monitoring/sync controls.

---

## Final Reflection

Starting with mock data helped me deliver a complete, testable product under assignment constraints.
If this project moved into production-like usage, the next milestone would be replacing seed generation with governed ingestion (API-first, scraper only where appropriate), while keeping the existing analytics and insight experience intact.
