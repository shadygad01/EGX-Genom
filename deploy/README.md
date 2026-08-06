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

## Continuous deployment (recommended): GitHub Actions → VPS

Steps 1-4 below are the one-time manual bootstrap. After that, every push
to `main` touching `deploy/`, `api/`, `web/`, `research/`, or
`package*.json` can redeploy automatically via
`.github/workflows/deploy-vps.yml` — it SSHs in, `git reset --hard
origin/main`, rebuilds, reruns `deploy/systemd/install.sh`, then runs the
same health checks as the "Verification checklist" below and **fails the
job loudly if any of them fail** (nothing is marked successful on a guess).

This requires three repository secrets that nobody but you can set — a
GitHub Actions runner has real internet access to reach your VPS; nothing
in this repo or any automated session does, by design, so this step can't
be done for you:

1. Generate a dedicated deploy keypair (do this on your own machine, not
   by pasting anything into an AI chat):
   ```bash
   ssh-keygen -t ed25519 -C "egx-genom-deploy" -f ./egx_deploy_key -N ""
   ```
2. Authorize the **public** half on the VPS (`ssh root@162.245.186.123`,
   or InterServer's web console if you'd rather not use the still-shared
   root password):
   ```bash
   mkdir -p ~/.ssh && chmod 700 ~/.ssh
   echo "<paste contents of egx_deploy_key.pub>" >> ~/.ssh/authorized_keys
   chmod 600 ~/.ssh/authorized_keys
   ```
   Prefer a dedicated non-root deploy user with narrow `sudo` rights over
   using `root` directly for CI, if you're willing to set that up — but
   `root` matches every other convention already in this `deploy/`
   directory (`egx-api.service`/`egx-collector.service` both run as
   `User=root`), so it's not a new risk relative to what's already here.
3. In GitHub: **Settings → Secrets and variables → Actions → New
   repository secret**, add:
   - `VPS_HOST` = `162.245.186.123`
   - `VPS_USER` = `root` (or your dedicated deploy user)
   - `VPS_SSH_KEY` = the **private** half (`cat egx_deploy_key`) — paste
     the whole thing, including the `-----BEGIN/END-----` lines
   - Delete `egx_deploy_key`/`egx_deploy_key.pub` locally once added, or
     keep them somewhere safe — GitHub never displays a secret's value
     again after you save it.
4. Rotate the root password (per the earlier warning in this
   conversation) — do it after step 2 if you authorized the deploy key as
   `root`, so the new deploy key survives the rotation.

Once the secrets exist, either push a qualifying change to `main`, or
trigger it manually from the Actions tab (or ask for a manual
`workflow_dispatch` run) — the job's own log is verifiable proof: it
prints `systemctl is-active` for every unit, real `curl` output from the
API/nginx/dashboard, and ends with `VERIFICATION PASSED` only if every
check actually succeeded.

## Manual deployment (one-off, or if you'd rather not wire up CI)

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
