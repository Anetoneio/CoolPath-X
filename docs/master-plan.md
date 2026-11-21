Full plan lives in the team's Claude Doc. This file is the working summary.

# Master plan — ASTRA COOLPATH X

**Mission.** Heat-aware, safety-first scheduling and routing for Ahmedabad municipal outdoor workers, using satellite thermal data, weather and GIS. Not just a heat map: it turns data into explainable workforce decisions.

**MVP.** Ahmedabad heat layer, 6-8 demo sites, heat-aware schedule within work-rest limits, route comparison (fastest vs lower exposure), data-confidence report, rest facility layer.

**Stretch** (only after the Hour 6 checkpoint passes): what-if simulator, Gujarati/Hindi worker cards, unsafe-condition report.

**Out of scope:** live satellite processing, GPS tracking, auth, WBGT hardware, multi-department coordination.

**Architecture.** Offline data scripts produce static layers in `data/processed`; FastAPI engine in `engine/` serves them with exposure scoring, scheduler, route compare and confidence; React + Vite + Leaflet in `web/` consumes the API.

**Timeline and checkpoints.**
- C0 at 0.5h — contracts frozen.
- C1 at 3h — heat grid and mock APIs render in the UI.
- C2 at 6h — end-to-end happy path plus scope cut decision.
- C3 at 7.5h — feature freeze.
- Demo-ready by 8.5h.

**Honesty rules.** Exposure values are estimates. Every recommendation has a plain-language `reason` string and a confidence score. Policy thresholds come from an official source cited in `contracts/policy.yaml` — never invented.
