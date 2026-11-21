# Seat B1: Dashboard

Owns: `web/`, except `web/src/components/confidence/`, `web/src/components/worker/` and `web/src/i18n/` (B2 owns those). Never edit `contracts/`.

Read first: `.clinerules`, `AGENTS.md`, `docs/master-plan.md`, `docs/HANDOFF.md`, `docs/status/B1.md`, `contracts/api.md`, `mocks/`.

## Tasks in order

1. Map with heat-layer toggle, site markers and facility markers (verified vs unverified styled differently).
2. Site selection plus a Generate Schedule button calling `POST /schedule`.
3. Schedule view: ordered timeline, rest breaks, and the reason text for each assignment.
4. Route comparison view: two routes in different colors, exposure badges, nearby water points.
5. **Stretch**, only after the Hour 6 checkpoint passes: what-if panel calling `POST /simulate`.
6. Responsive polish.

**Rules:** all calls go through one API client file using the single base-URL constant; use mock endpoints until the engine is ready; label every score as an estimate.

**Done when:** the happy path works end to end against the engine with no console errors.

**Handoff duty:** update `docs/status/B1.md` and commit after each task.
