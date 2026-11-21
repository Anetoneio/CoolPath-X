# ASTRA COOLPATH X — Deployment Guide (Free Hosting)

This guide documents how to deploy the COOLPATH X project on free hosting services:
- **Backend (Engine)**: Render (Python Web Service)
- **Frontend (Web)**: Vercel (Vite Static Site)

---

## Architecture Overview

```
 [User Browser]
       │
       ▼
 ┌───────────────┐                  ┌────────────────────────┐
 │ Vercel (Web)  │  HTTPS API calls │ Render (FastAPI Engine)│
 │ Vite + React  ├─────────────────►│ Port $PORT             │
 └───────────────┘ (VITE_API_BASE_URL)└────────────────────────┘
```

---

## 1. Engine Deployment on Render (Python Web Service)

Render provides free hosting for Python web services.
> [!NOTE]
> Render free web services spin down after 15 minutes of inactivity. When a new request arrives, a cold start takes approximately 30–50 seconds.

### Option A: Automated Blueprint Deployment (via `render.yaml`)
If your Render account allows Blueprints without upfront card entry:
1. Push your repository to GitHub.
2. In the Render Dashboard, click **New +** > **Blueprint**.
3. Connect your repository. Render will detect `render.yaml` at the root and configure the service automatically.
4. Click **Apply**.

### Option B: Manual Service Creation (Dashboard)
Render's free tier may request a credit card for Blueprint setup; if preferred, create the service manually without blueprints:
1. In the Render Dashboard, click **New +** > **Web Service**.
2. Connect your GitHub repository.
3. Configure the service settings:
   - **Name**: `coolpath-engine` (or your choice)
   - **Region**: Choose the closest region (e.g., Singapore or Frankfurt)
   - **Branch**: `main`
   - **Root Directory**: Leave blank (root of repository)
   - **Runtime**: `Python 3`
   - **Build Command**: `pip install -r engine/requirements.txt`
   - **Start Command**: `uvicorn engine.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. Add Environment Variables under **Advanced**:
   - `PYTHON_VERSION`: `3.11.9`
   - `DATA_MODE`: `real` (or `mock` if testing strictly with mocks)
   - `ALLOWED_ORIGINS`: `http://localhost:5173` (can add your custom Vercel domain once deployed; preview domains matching `^https://.*\.vercel\.app$` are allowed automatically)
5. Click **Create Web Service**.
6. Once deployed, note your service URL: `https://<your-service-name>.onrender.com`.

---

## 2. Web Deployment on Vercel (Vite Static Site)

Vercel provides free global CDN hosting for Vite/React applications.

### Setup Steps:
1. In the Vercel Dashboard, click **Add New...** > **Project**.
2. Import your GitHub repository.
3. In **Configure Project**:
   - **Framework Preset**: `Vite`
   - **Root Directory**: Click **Edit** and select `web` (very important!).
   - **Build Command**: `npm run build` (or `vite build`)
   - **Output Directory**: `dist`
   - **Install Command**: `npm install`
4. Expand **Environment Variables**:
   - Name: `VITE_API_BASE_URL`
   - Value: `https://<your-service-name>.onrender.com` (your live Render engine URL without trailing slash)
5. Click **Deploy**.

Vercel uses `web/vercel.json` for SPA route rewrites to ensure direct page loads and refreshes work smoothly.

---

## 3. Environment Variables Reference

| Service | Variable Name | Default / Example | Purpose |
|---|---|---|---|
| **Web** (Vercel) | `VITE_API_BASE_URL` | `http://localhost:8000` | Points frontend fetch calls to the engine API |
| **Engine** (Render) | `PORT` | `8000` | Port bound by Uvicorn (Render sets this dynamically) |
| **Engine** (Render) | `DATA_MODE` | `mock` (set to `real` in prod) | Switches between mock data and real pipeline data |
| **Engine** (Render) | `ALLOWED_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated CORS allowed origins |
| **Engine** (Render) | `PYTHON_VERSION` | `3.11.9` | Python runtime version for Render |

---

## 4. Verification Checklist

- [ ] `GET https://<your-engine>.onrender.com/health` returns `{"status":"ok","data_mode":"real"}`
- [ ] `GET https://<your-engine>.onrender.com/sites` returns 8 municipal sites
- [ ] Vercel site loads map, renders heat layer toggle, site markers, and water/shade facilities
- [ ] Schedule generation returns assignments with plain-language reason strings
