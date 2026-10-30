# NIRIKSH deployment guide (Vercel + Render)

This prototype has a static HTML/JavaScript frontend and a FastAPI backend. Deploy them as two services.

## 1. Deploy the backend on Render

- Create a **Web Service** from this GitHub repository.
- Root Directory: `backend`
- Runtime: `Python 3`
- Build Command: `pip install -r requirements.txt`
- Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
- Add environment variable `NIRIKSH_CORS_ORIGINS` with the exact Vercel origin, e.g. `https://your-project.vercel.app` (no trailing slash).
- After deployment, test `https://YOUR-RENDER-SERVICE.onrender.com/api/health`.

### Persistence warning

The prototype uses SQLite and saves uploaded PDFs to disk. Render's ordinary ephemeral filesystem can lose database changes and uploads on restart/redeploy. For persistence, attach a Render persistent disk (mount path `/var/data`) and set:

- `NIRIKSH_DB_PATH=/var/data/niriksh_demo.db`
- `NIRIKSH_UPLOAD_DIR=/var/data/uploads`

The persistent disk may require a paid Render service. Without it, treat the hosted instance as a temporary demo; do not enter real institutional data. The initial sample data is seeded automatically when the database is empty.

## 2. Point the frontend at the backend

Edit `frontend/public/config.js` and replace the local URL with the deployed Render URL, e.g. `https://YOUR-RENDER-SERVICE.onrender.com`. Do not add a trailing slash. Commit and push this change.

## 3. Deploy the frontend on Vercel

- Import the same GitHub repository as a new Vercel project.
- Root Directory: `frontend`
- Framework Preset: `Other`
- Build Command: leave empty
- Output Directory: `public`
- Install Command: leave empty
- Deploy.

If the Vercel domain differs from the origin configured in Render, update `NIRIKSH_CORS_ORIGINS` in Render to the exact deployed origin and redeploy/restart the backend.

## 4. Smoke test

Open the Vercel site and test both portals, login, dashboard loading, case details, compliance checks, PDF display/upload, clarification/resubmission, EVC and audit logs. If requests fail, check browser Developer Tools → Network/Console and Render logs.

## Notes

- This is a synthetic-data SIH prototype, not a production AICTE system.
- Keep demo credentials and synthetic data only. Do not upload real institution documents.
- Vercel hosts only the static frontend; it does not run this FastAPI backend.
