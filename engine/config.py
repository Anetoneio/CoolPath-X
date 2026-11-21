"""Runtime configuration for the COOLPATH X engine.

DATA_MODE controls where static data is read from:
  - "mock"  -> read from /mocks (demo-safe, always available)
  - "real"  -> read from /data/processed (A1-produced pipeline output)

Set via the DATA_MODE environment variable. Defaults to "mock".
Never hardcode values that belong in contracts/policy.yaml.
"""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
PROJECT_DIR = APP_DIR.parent

DATA_MODE = os.getenv("DATA_MODE", "mock").lower()

MOCKS_DIR = PROJECT_DIR / "mocks"
RESPONSES_DIR = MOCKS_DIR / "responses"
PROCESSED_DIR = PROJECT_DIR / "data" / "processed"

CACHE_DIR = APP_DIR / "cache"
FORECAST_CACHE = CACHE_DIR / "forecast.json"

POLICY_FILE = PROJECT_DIR / "contracts" / "policy.yaml"

if DATA_MODE not in ("mock", "real"):
    raise ValueError(f"DATA_MODE must be 'mock' or 'real', got {DATA_MODE!r}")