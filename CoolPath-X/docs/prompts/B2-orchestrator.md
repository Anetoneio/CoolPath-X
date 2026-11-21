# Seat B2: Orchestrator and worker view

Owns: `contracts/`, `mocks/`, `docs/`, `web/src/components/confidence/`, `web/src/components/worker/`, `web/src/i18n/`.

Read first: `.clinerules`, `AGENTS.md`, `docs/master-plan.md`, `docs/HANDOFF.md`, `docs/DECISIONS.md`, `docs/status/*.md`.

## Tasks in order

1. Verify contracts and mocks match each other. Fill `contracts/policy.yaml` only from an official source and cite it in `source_citation`. Do not invent thresholds.
2. At each checkpoint (C0 to C3): read all `docs/status` files, merge seat branches into `main`, run the acceptance checks, record decisions in `docs/DECISIONS.md`.
3. **Confidence panel component** showing the overall score, each component, and the notes.
4. **Worker task card** (mobile-first) in English, Gujarati and Hindi using fixed pre-written strings in `web/src/i18n/`, plus an unsafe-condition report form that saves to a local JSON file or endpoint stub.
5. **Demo script**, 6-slide pitch outline, and a backup demo video at Hour 8.

**Done when:** `main` passes all acceptance checks at C3 and the demo runs from a clean clone.

**Handoff duty:** update `docs/status/B2.md` and commit after each task.
