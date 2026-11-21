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
- Commit small and often. Ask before installing any new dependency.
- Before finishing any task, list which files you changed and which contract you verified against.

## Checkpoints

- C0 at 0.5h — scaffold complete (this phase).
- C1 at 3h — endpoints serving mocks; map renders markers.
- C2 at 6h — scope cut: no new features after this point.
- C3 at 7.5h — feature freeze: bug fixes only.