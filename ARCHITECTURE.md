# GapSight Architecture (Brief)

This document explains the architecture at a high level and why each part exists.

## 1) System Overview
GapSight is a two-tier web app:

- **Frontend**: React (Vite) deployed on Vercel
- **Backend API**: FastAPI deployed on Render
- **Database**: Supabase (Postgres)
- **AI Provider**: Groq API for insight generation

Flow:
1. Frontend requests analytics/competitor/insight/report endpoints.
2. FastAPI routers fetch and aggregate data from Supabase.
3. For insights, backend builds a strict prompt and asks Groq.
4. Backend returns normalized JSON for charts/cards.
5. Reports endpoint can export CSV/PDF.

## 2) Backend Design
Backend is organized by feature routers:
- `analytics.py`: personal performance analytics
- `competitors.py`: competitor comparisons and gap logic
- `insights.py`: AI + rules-based insight generation and action playbooks
- `reports.py`: CSV/PDF exports

Shared concerns:
- `database.py`: Supabase client + retry helper
- `seed.py`: mock data generation and insertion

Why this structure:
- Keeps each feature isolated and readable
- Makes it easier to evolve one module without touching all others

## 3) Data Model (Conceptual)
Main entities:
- `users`
- `follower_metrics`
- `posts`
- `competitors`
- `competitor_metrics`

This model supports:
- time-series trend charts
- engagement calculations
- content-type comparisons
- competitor benchmarking

## 4) AI Insights Layer
`insights.py` follows a resilient pattern:
- Build quantitative summary from DB
- Build competitor content gaps
- Generate baseline rule-based insights
- Attempt AI completion with strict JSON contract
- Fallback to baseline if AI is unavailable

Why this approach:
- Avoids total failure when AI service/key has issues
- Keeps UX stable and predictable

## 5) Deployment Topology
- Vercel serves frontend static app.
- Render serves backend API.
- Supabase stores persistent data.
- UptimeRobot pings `/health` to reduce Render cold starts.

## 6) Mock Data Strategy
Data is seeded once via `backend/app/seed.py`.
- It uses Faker/randomized generation to create realistic social metrics.
- Data does **not** update automatically unless seed script is rerun or write jobs are added.

Why this was chosen:
- Assignment explicitly permits mocked data.
- Enables full analytics/AI/reporting pipeline demonstration without external API dependencies.

## 7) Trade-offs
- Pros:
  - Fast delivery and strong feature coverage
  - Realistic analytics behavior from seeded time-series data
  - Clear modular codebase
- Cons:
  - Single default user (`my_brand`) limits multi-user realism
  - No true scheduled automation jobs yet
  - Seeded data randomness can vary results between runs

## 8) Future Extension Path
- Add auth + per-user tenancy
- Replace seeded inputs with real social platform connectors
- Add scheduled workflows (e.g., weekly recommendations persisted)
- Add automated tests and observability
