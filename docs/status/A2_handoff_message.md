**A2 (Engine) Handoff Update**

The engine is verified and ready on branch `a2-engine`. All 30 unit and regression tests pass in both `DATA_MODE=mock` and `DATA_MODE=real`. `python verify.py` passes all checks with `READY TO PUSH`.

**Quick Run:**
```bash
cd engine && python -m pip install -r requirements.txt
python verify.py        # pre-push verification gate
python main.py          # live API at http://localhost:8000/docs
```

**Key Limitations to Know:**
1. **Mock spatial gaps & fallback:** 5 of 8 mock sites sit outside the 20 mock heat-grid cells and return the 50 mid-range fallback score. Real data from A1 is needed for full coverage.
2. **Real mode serves mocks:** `data/processed/` is unpopulated; engine falls back to static mocks gracefully.
3. **Multi-crew capacity & omissions:** Sites fitting across available crews are scheduled; any site exceeding capacity is omitted as `contracts/api.md` defines no omission field.

**Next Steps:**
- **A1:** Supply full-coverage processed data in `data/processed/` and replace `TODO_VERIFY` values in `contracts/policy.yaml`. See `docs/status/A2.md` for the placeholder registry.
- **B1 (Frontend):** Wire UI to show assignment `reason`, `rest_breaks`, `confidence`, and route `water_points_nearby`.
