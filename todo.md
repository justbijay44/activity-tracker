# Activity Tracker — TODO / Roadmap

A backlog to pick from one item at a time — not a commitment list. Two goals shape priority:
1. **Product** — usable, self-hostable by others
2. **Portfolio** — demonstrates skills for AI/ML, Data Analyst, Data Engineering, and Backend roles

## Status
- v2: Docker, multi-provider AI scaffolding, domain dedup, batch classification — done
- v3: Custom URL rules, new charts, prompt consistency, (url, title) classification fix, indexes, timezone fix — done

## Next up
- [ ] **Daily time limits + alerts** — flag excessive time on unproductive sites (needs design: dashboard only, or extension popup too?)
- [ ] **Prompt tuning** — based on real-world testing feedback

## Product direction
- [ ] Migrate SQLite → Postgres (planned, ties into Data Engineering items below)
- [ ] Multi-user accounts / auth
- [ ] BYOK (Groq/Gemini keys) — once accounts exist
- [ ] Self-host packaging — clearer setup docs, maybe one-command install
- [ ] Settings/onboarding UI in dashboard or extension

## Feature ideas
- [ ] History/trends view (weekly/monthly, not just daily)
- [ ] Data export (CSV/JSON) of sessions/summaries
- [ ] Idle detection within the browser (not just leaving the browser)
- [ ] Categories/projects beyond productive/unproductive/neutral (e.g. "Work - Client A")
- [ ] Focus mode — block/warn on unproductive sites during chosen hours, using existing custom rules
- [ ] Multi-browser support (Firefox/Edge — currently Chrome MV3 only)

## Portfolio-building ideas (by role)

### AI/ML Engineering
- [ ] Build an eval set (hand-labeled sessions) + accuracy/consistency metrics for the classifier
- [ ] Compare providers/models (Ollama vs Groq vs Gemini) on accuracy, cost, latency
- [ ] Embedding-based similarity cache — classify near-duplicate titles/URLs without a fresh LLM call
- [ ] Use accumulated labels (custom rules + AI history) to train/fine-tune a lightweight classifier as an alternative to prompting

### Data Analyst
- [ ] Weekly/monthly trend views, productivity score over time
- [ ] "Most productive hours/days" insights
- [ ] Streaks / goal tracking
- [ ] Exportable reports (CSV/PDF summary)

### Data Engineering
- [ ] Migrate SQLite → Postgres
- [ ] Daily rollup/aggregation tables (pre-computed summaries instead of live aggregation on every dashboard load)
- [ ] Data retention/archival policy for raw session data
- [ ] Basic data quality monitoring (e.g. track % unclassified over time)

### Backend
- [ ] Test suite (pytest) for API endpoints
- [ ] DB migrations (Alembic) instead of `create_all`
- [ ] Background task queue for AI classification (avoid blocking request on LLM call)
- [ ] CI pipeline (GitHub Actions: lint + tests)
- [ ] Logging/observability
- [ ] Auth (JWT) once multi-user lands

## Not now / future
- Hosted multi-tenant version
- Mobile companion app
