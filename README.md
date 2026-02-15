# AI Watch

Track AI service subscriptions, accounts, budgets, and recommendations from one Flask app.

## Run locally

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

App URL: `http://localhost:5000`

## Deploy to Render

### Option A: Blueprint (`render.yaml`) - fastest

1. Push this repository to GitHub.
2. In Render, click **New +** -> **Blueprint**.
3. Select your repo and create the service.
4. Render reads `render.yaml` and deploys automatically on the free plan using ephemeral storage.

### Option B: Manual Web Service setup

1. In Render, click **New +** -> **Web Service** and connect your repo.
2. Use:
   - Runtime: `Python`
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn --bind 0.0.0.0:$PORT app:app`
   - Health Check Path: `/api/health`
3. Add environment variable:
   - `AI_WATCH_DB_PATH=data/db.json`
4. (Optional) add a persistent disk and set `AI_WATCH_DB_PATH=/var/data/db.json`.
5. Deploy.

### Keep data between deploys/restarts (recommended)

Render instances use ephemeral filesystem by default. To persist app data instead:

1. Add a persistent disk in Render and mount it at `/var/data`.
2. Set `AI_WATCH_DB_PATH=/var/data/db.json`.
3. Redeploy.
4. Use a paid plan (`starter` or higher), since persistent disks are not available on `free`.

## Notes

- `app.py` exposes `app` for Gunicorn.
- `requirements.txt`, `runtime.txt`, and `Procfile` are included for deployment compatibility.
