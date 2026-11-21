**A2 (Engine) Handoff Update**

The engine is verified and ready on branch `a2-engine` (commit `3d33b83`). All 29 unit and regression tests pass in both `DATA_MODE=mock` and `DATA_MODE=real`. `python verify.py` passes all checks with `READY TO PUSH`.

**Quick Run:**
```bash
cd engine && python -m pip install -r requirements.txt
python verify.py        # pre-push verification gate
python main.py          # live API at http://localhost:8000/docs
```

**Key Limitations to Know:**
1. **Exposure values are estimates:** All scores are 0–100 estimates; every score includes a plain-language `reason` string that UI must display.
2. **Real mode currently falls back to mocks:** `data/processed/` is unpopulated, so real mode serves static mocks safely without failing.
3. **Identical mock routes:** On current mock sites, Route B matches Route A with label `"Same as fastest route (no lower-exposure alternative)"`.

**Next Steps:**
- **A1:** Populate `data/processed/` and replace `TODO_VERIFY` values in `contracts/policy.yaml`. See `docs/status/A2.md` for the full placeholder registry.
- **Frontend (B1):** Wire UI to show assignment `reason`, `rest_breaks`, `confidence`, and route `water_points_nearby`.
