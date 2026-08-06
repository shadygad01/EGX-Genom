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

## Continuous deployment (recommended): the VPS pulls from GitHub itself

No SSH keys, no GitHub secrets, no credentials anywhere. This repo is
public, so `git fetch` needs no authentication — the VPS reaches out to
GitHub on its own schedule (same "pull, don't get pushed to" shape as
`egx-collector.timer` already uses for market data), instead of GitHub
reaching into the VPS.

`deploy/systemd/egx-deploy.timer` fires `egx-deploy.service` every 5
minutes, which runs `deploy/systemd/auto-deploy.sh`:
1. `git fetch origin main`; if `HEAD` already matches `origin/main`, it
   exits immediately — no wasted rebuilds when nothing changed.
2. Otherwise: `git reset --hard origin/main` (only affects tracked files
   — `egx-collector.service`'s own runtime output under `research/data/`
   is untracked and untouched), rebuild (`uv sync --frozen`, `npm ci`,
   `npm run build -w api`, `npm run build -w web -- --mode selfhosted`),
   rerun `deploy/systemd/install.sh`.
3. Verify: `systemctl is-active` on `egx-api.service`/`nginx`, real
   `curl` checks against the API directly and through nginx, and the
   dashboard's HTTP status — printed to the journal either way, and the
   unit is left in `failed` state if any check doesn't actually pass
   (`journalctl -u egx-deploy` / `systemctl status egx-deploy.service` is
   your evidence, not a guess).

This installs automatically as part of `deploy/systemd/install.sh` (step
4 below) — nothing else to configure. To confirm it's live and see proof
of the last run:

```bash
systemctl list-timers egx-deploy.timer --no-pager   # shows next scheduled check
journalctl -u egx-deploy.service --no-pager | tail -40
# Force an immediate check instead of waiting up to 5 minutes:
systemctl start egx-deploy.service && journalctl -u egx-deploy.service -f
```

The only remaining manual credential on this box is the root
password used to reach it at all (SSH / the InterServer console) — rotate
it per the earlier warning in this conversation; nothing added here
depends on it.

## Manual deployment (one-off, or if you'd rather not wire up auto-deploy)

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

This installs and starts `egx-api.service` (the live backend),
`egx-collector.service`/`egx-collector.timer` (the every-minute data
refresh that keeps both the API's and the static site's data current), and
`egx-deploy.service`/`egx-deploy.timer` (the every-5-minute check for new
commits on `main` — see "Continuous deployment" above), then runs a
`curl 127.0.0.1:3001/health` sanity check at the end.

## Verification: is the migration actually complete and correct?

Run this **on the server**, anytime:

```bash
bash /opt/egx-genom/deploy/verify.sh
```

It answers exactly the three things that matter, with real evidence, not
a guess, and exits non-zero if anything is wrong:

1. **Is the server running the latest code?** Compares the server's `git`
   `HEAD` against `origin/main` directly — the same check
   `egx-deploy.service` uses to decide whether to redeploy at all.
2. **Are all the services actually up?** `systemctl is-active` on
   `egx-api.service`, `egx-collector.timer`, `egx-deploy.timer`, `nginx`.
3. **Do the live features actually work**, not just the static ones? Real
   `curl` calls to the API directly, through nginx, the dashboard's HTTP
   status, and a real `POST /api/decisions` call — a `501` there means
   Decision Center/Capital Allocation are still silently unconfigured
   even if everything else is green.

Paste the full output back if you want it reviewed — that's the
"دليل وبرهان" (evidence and proof): every line is either a real command's
real output or an explicit `PASS`/`FAIL`, never an assumption.

### Manual checklist (what `verify.sh` automates)

The individual commands below are what the script above already runs for
you — kept here for when you want to debug one specific piece by hand
instead of the full sweep (or paste the output back for review — this
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
