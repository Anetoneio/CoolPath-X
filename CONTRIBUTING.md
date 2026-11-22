# Contributing Guidelines (governance branch)

## Branch‑per‑seat workflow
- Each seat works on its own long‑living branch:
  - `a1-data`
  - `a2-engine`
  - `b1-web`
  - `b2-orch`
- The orchestrator merges to `main` only at the defined checkpoints (C0‑C3).

## Folder ownership
- `/data` & data scripts → **A1**
- `/engine` → **A2**
- `/web` (frontend) → **B1**
- `/contracts`, `/mocks`, `/docs` → **B2**
- The ownership map is documented in `AGENTS.md` and `.clinerules`.

## Contract‑first rule
- All changes must be reflected in a contract file before touching code.
- Contracts live under `/contracts` and are reviewed by the orchestrator.

## Review rules
- Every pull request requires **one approval** and a **green CI** status.
- Changes to any of the following paths need the maintainer’s explicit approval (enforced by CODEOWNERS):
  - `/contracts/`
  - `/contracts/policy.yaml`
  - `/docs/prompts/`
  - `/render.yaml`
  - `/.github/`
  - `/LICENSE`
  - `/data/SOURCES.md`
- The pull‑request template (see `.github/pull_request_template.md`) must be completed.

## Outside contributors
- Fork the repository, create a branch from `main`, and open a pull request.
- For large or contract‑affecting changes, **open an issue first** and discuss with the maintainers.
- Follow the same review rules as internal contributors.
