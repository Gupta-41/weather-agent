# Deploying

Backend to Render, frontend to Vercel. Do the backend first — the frontend
needs its URL, and the backend needs the frontend's origin, so there is one
unavoidable back-and-forth at the end.

## 1. Backend on Render

1. Push this repo to GitHub.
2. Render → **New → Blueprint** → pick the repo. It reads `render.yaml`.
3. Set the two secrets it asks for:
   - `ANTHROPIC_API_KEY` — your key.
   - `CORS_ORIGINS` — leave it as `http://localhost:5173` for now; you'll come
     back and add the Vercel URL in step 3.
4. Deploy, then check `https://<your-service>.onrender.com/api/health`. You want
   `"llm_configured": true`. If it's `false`, the key didn't save.

The blueprint mounts a 1 GB disk at `/var/data`. Without it Render wipes the
filesystem on every deploy and your saved locations vanish — which is exactly
the kind of thing that breaks during a demo rather than during testing.

**Free tier spins down after inactivity.** The first request after a quiet
period takes 30–50 seconds, and the background alert poller doesn't run while
the service is asleep. Before you present, hit the health endpoint once to wake
it, then press **Check now** in the alerts panel.

## 2. Frontend on Vercel

1. Vercel → **New Project** → same repo → set **Root Directory** to `frontend`.
2. Add an environment variable:
   - `VITE_API_BASE` = `https://<your-service>.onrender.com` (no trailing slash)
3. Deploy. `vercel.json` already sets the build command and SPA rewrites.

Vite inlines `VITE_API_BASE` at build time, so changing it later needs a
redeploy, not just a restart.

## 3. Close the loop

Go back to Render and set `CORS_ORIGINS` to your Vercel URL, comma-separated if
you want localhost too:

```
https://weathergpt.vercel.app,http://localhost:5173
```

Save. Render restarts automatically. If the deployed frontend loads but every
request fails, this is the reason — check the browser console for a CORS error
before looking anywhere else.

## Docker, if you'd rather

```bash
docker build -t weathergpt .
docker run -p 8000:8000 -v weathergpt-data:/data \
  -e ANTHROPIC_API_KEY=sk-... \
  -e CORS_ORIGINS=http://localhost:5173 \
  weathergpt
```

## Demo-day checklist

- [ ] `/api/health` returns `llm_configured: true`
- [ ] Backend woken up within the last few minutes
- [ ] At least one location saved, with a live alert showing
- [ ] A question asked in Hindi or Telugu, to show the language switch working
- [ ] The trace panel opened at least once — it's the compulsory add-on and the
      thing judges are scoring
- [ ] Voice tested **in Chrome**; Firefox has no Web Speech recognition

## Fallback if the venue wifi is bad

Run both locally. The backend needs outbound access to Open-Meteo and the
Anthropic API, but nothing inbound:

```bash
uvicorn backend.main:app --reload            # terminal 1
cd frontend && npm run dev                   # terminal 2
```
