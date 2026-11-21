A2 (Engine) update - branch a2-engine, code commit 346cdc1

Ready: all 7 endpoints are live. 33 tests pass in mock and real mode, and `python verify.py` prints READY TO PUSH.
Run it: cd engine; pip install -r requirements.txt; python main.py; Swagger UI at http://localhost:8000/docs

New since last update:
- /schedule now uses every requested crew (it used to drop a site when crews > 1).
- A site outside every heat-grid cell uses the nearest cell if it is within 1 km, with lower confidence and a reason that names the cell and distance. Beyond 1 km the score is a flat mid-range 50.

Limitations:
1. All scores are estimates. The UI should show every reason and confidence value.
2. DATA_MODE=real serves mocks until data/processed/ exists.
3. On the mocks, S07 and S08 are over 1 km from the grid and get the flat 50.
4. The forecast is for today (November), so time-of-day effects are small below the 25C baseline. /simulate on early-morning starts may show identical exposure.
5. /route/compare can return identical routes (S01 to S02 is 66 vs 66). POST /schedule with an unknown site id returns an empty list with 200.

A1: replace the TODO_VERIFY keys in contracts/policy.yaml and make sure data/processed/ covers every site location.
Frontend: show reason, confidence, rest_breaks and water_points_nearby.