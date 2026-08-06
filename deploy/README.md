# Self-hosted VPS deployment runbook

This is for a **private, self-hosted** instance of AGX (e.g. a personal VPS)
running the live `api/` so Decision Center (`POST /decisions`) and Capital
Allocation (`POST /capital-allocation`) work with real holdings — the
"local-only/self-hosted" option `docs/ARCHITECTURE_DECISIONS.md`'s AD-57
names as permanent and always available, just hosted remotely instead of on
a laptop.

This is **not** the public GitHub Pages deployment (`.github/workflows/deploy-pages.yml`,
untouched by any of this) and does not change it. AD-57 keeps that one
static-only, permanently, by design.

## Layout on the server

Everything below assumes the repo is checked out at `/opt/egx-genom`. Adjust
every path in the two systemd units and `deploy/nginx/egx-genom.conf` if you
use a different directory.

## 1. Build

```bash
cd /opt/egx-genom

# Python research engine + its CLI (needed at runtime too: egx-api.service's
# /decisions and /capital-allocation routes shell out to `uv run ... agx_research.cli`).
cd research && uv sync && cd ..

# api/ + web/. web MUST build with --mode selfhosted, not the default
# production mode -- web/.env.production hard-codes VITE_DATA_PROVIDER=static
# (the GitHub Pages build); web/.env.selfhosted overrides it to "api" so the
# dashboard actually calls the live backend instead of reading bundled JSON.
npm install
npm run build -w api
npm run build -w web -- --mode selfhosted
```

Confirm the web build picked up the right provider — grep the built bundle:

```bash
grep -o '"api"' web/dist/assets/*.js | head -1   # should find a match
```

## 2. Seed runtime data

`egx-api.service` reads from `/opt/egx-genom/research/data` and
`/opt/egx-genom/web/public/data` — both are written by a real
`agx run`/`agx_research.cli run`, same as `egx-collector.service` performs
on its own 1-minute timer once installed (step 4). If this is the very
first deploy, run it once by hand first so the API has something to serve
immediately instead of empty artifacts:

```bash
cd /opt/egx-genom/research
uv run python -m agx_research.cli run --mode live \
  --date "$(date +%F)" \
  --data-dir /opt/egx-genom/research/data \
  --dashboard-out /opt/egx-genom/web/public/data
```

## 3. Install nginx site

```bash
cp deploy/nginx/egx-genom.conf /etc/nginx/sites-available/egx-genom.conf
ln -sf /etc/nginx/sites-available/egx-genom.conf /etc/nginx/sites-enabled/egx-genom.conf
nginx -t
systemctl reload nginx
```

## 4. Install + start the systemd units (api + collector)

```bash
cd /opt/egx-genom
bash deploy/systemd/install.sh
```

This installs and starts `egx-api.service` (the live backend) and
`egx-collector.service`/`egx-collector.timer` (the every-minute data
refresh that keeps both the API's and the static site's data current), and
runs a `curl 127.0.0.1:3001/health` sanity check at the end.

## Verification checklist

Run these **on the server** (or paste the output back for review — this
sandbox cannot reach the VPS directly: it's not on this session's network
egress allowlist, and SSH/raw TCP isn't proxied even for allowed hosts):

```bash
# 1. Both services are active
systemctl is-active egx-api.service egx-collector.timer nginx

# 2. API answers directly
curl -s http://127.0.0.1:3001/health
curl -s http://127.0.0.1:3001/system-status | head -c 300

# 3. Through nginx, at the real path the browser uses
curl -s http://127.0.0.1/EGX-Genom/ | grep -o '<title>[^<]*</title>'
curl -s http://127.0.0.1/api/health

# 4. The live-only routes actually work end to end (not 501 "not configured")
curl -s -X POST http://127.0.0.1/api/decisions \
  -H 'Content-Type: application/json' \
  -d "{\"date\":\"$(date +%F)\"}" | head -c 300
# A 501 here means DECISION_DATA_DIR doesn't point at real `agx run` output
# yet -- re-check step 2, or that egx-collector.timer has run at least once.

# 5. Dashboard data is fresh, not stale from an old run
curl -s http://127.0.0.1:3001/system-status | grep -o '"generated_at":"[^"]*"\|"pipeline_run_date":"[^"]*"'
journalctl -u egx-collector.service --since "-10 min" --no-pager | tail -30

# 6. web build really used the api provider, not static
grep -o 'VITE_DATA_PROVIDER[^,}]*' /opt/egx-genom/web/dist/assets/*.js 2>/dev/null | head -3
```

If any of these fail, the two most common causes are:

- **`/api/decisions` returns 501** — `DECISION_DATA_DIR` in
  `egx-api.service` doesn't match the `--data-dir` the collector/manual run
  actually used, or no run has completed yet. Fix the env var or run step 2
  again, then `systemctl restart egx-api.service`.
- **Dashboard loads but every panel is empty / falls back to static-looking
  behavior** — the web build was made without `--mode selfhosted`, so it
  shipped `VITE_DATA_PROVIDER=static` and never calls `/api/*` at all.
  Rebuild per step 1.
