# AGENTS.md — ASTRA COOLPATH X ownership map

## Team ownership

- **/data and data pipeline scripts: A1** — satellite and geo data (heat grid, facilities sourcing).
- **/engine: A2** — FastAPI backend, scheduler, scoring.
- **/web: B1** — dashboard frontend (React + Vite + Leaflet + Tailwind).
- **/contracts, /mocks, /docs: orchestrator (B2)** — API contracts, mock data, documentation.

## Rules (from .clinerules)

- Only edit files inside the folder you were assigned. Never edit /contracts without explicit instruction.
- Every API response must match its file in /contracts. Check before marking a task done.
- Never hardcode values that belong in contracts/policy.yaml.
- Every score shown to users must carry a plain-language `reason` string.
- Exposure values are estimates. Label them as such in code comments and UI text.
- No secrets or API keys in the repo.

## Where to start

Each seat begins with its task prompt and the resume template:

- **A1 (data):** read `docs/prompts/A1-data.md`, then `docs/prompts/RESUME.md` with `<SEAT>` = A1.
- **A2 (engine):** read `docs/prompts/A2-engine.md`, then `docs/prompts/RESUME.md` with `<SEAT>` = A2.
- **B1 (dashboard):** read `docs/prompts/B1-dashboard.md`, then `docs/prompts/RESUME.md` with `<SEAT>` = B1.
- **B2 (orchestrator):** read `docs/prompts/B2-orchestrator.md`, then `docs/prompts/RESUME.md` with `<SEAT>` = B2.

All prompts list `.clinerules` first in their read-first list. The root `README.md` and `AGENTS.md` remain the entry points for running the project and understanding ownership.
- Commit small and often. Ask before installing any new dependency.
- Before finishing any task, list which files you changed and which contract you verified against.

## Checkpoints

- C0 at 0.5h — scaffold complete (this phase).
- C1 at 3h — endpoints serving mocks; map renders markers.
- C2 at 6h — scope cut: no new features after this point.
- C3 at 7.5h — feature freeze: bug fixes only.