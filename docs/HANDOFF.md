# Handoff protocol — ASTRA COOLPATH X

## Why
Claude usage limits may run out mid-task. We have two Claude accounts. Work continues from the repo, never from chat memory.

## Rules

**Rule 1:** Update `docs/status/<SEAT>.md` after every finished task, at every checkpoint, and immediately when Claude warns about low usage.

**Rule 2:** Make a commit when you update status. Use messages like `wip(A1): heat grid clipped, LST not normalised yet`.

**Rule 3:** To switch accounts, open Claude on the other account and paste `docs/prompts/RESUME.md` with your seat filled in.

**Rule 4:** Ask Claude for plans and task prompts once, save them in your seat prompt or status file, and have Cline read files by path instead of pasting file contents into chat.

## Git workflow

- One branch per seat: `a1-data`, `a2-engine`, `b1-web`, `b2-orch`.
- Work only in your owned folders.
- The orchestrator merges to `main` at checkpoints C0 to C3 only.
- Contract changes go through the orchestrator and are announced in the team chat and `docs/DECISIONS.md`.

## Ownership detail

- `/data` and data scripts = A1.
- `/engine` = A2.
- `/web` = B1, except `web/src/components/confidence/`, `web/src/components/worker/` and `web/src/i18n/` = B2.
- `/contracts`, `/mocks`, `/docs` = B2.

## Large files
`data/raw/` is git-ignored. Share raw downloads through the team's shared drive, not git.
