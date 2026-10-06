# CI/CD

```
pull request ──► Backend CI ─┐
                 Frontend CI ├─► must be green to merge into main (branch protection)
                 Docker Images (build only) ─┘

merge to main ─► Docker Images (build + push to ghcr.io, tags: latest and sha-<7>)
                       │
        you click "Run workflow" ─► Deploy ─ssh─► VPS: pull images, restart backend + frontend
```

| Workflow | File | Runs on | Does |
|---|---|---|---|
| Backend CI | `.github/workflows/backend-ci.yml` | PR, push to main | ruff, `db/schema.sql`, Alembic, import smoke test, pytest (Postgres 16 service) |
| Frontend CI | `.github/workflows/frontend-ci.yml` | PR, push to main | oxlint, `tsc -b` (strict), `vite build` |
| Docker Images | `.github/workflows/docker-images.yml` | PR (build only), push to main (build + push) | builds `dashboard-backend` and `dashboard-frontend`, publishes to GHCR |
| Deploy | `.github/workflows/deploy.yml` | manual (`workflow_dispatch`) | runs `deploy/remote-deploy.sh` on the VPS over SSH |

Deploy is manual on purpose while you learn what a deployment looks like. Making it automatic later is a
one-line trigger change.

## One-time setup

**1. Check the VPS architecture.** Images are built for `linux/amd64`.

```bash
uname -m        # x86_64 = fine. aarch64 = change `platforms:` in docker-images.yml to linux/arm64
```

**2. Let the first image build run.** Merging the PR that adds `docker-images.yml` to `main` triggers it.
Then open GitHub -> your profile -> Packages, and for both `dashboard-backend` and `dashboard-frontend`:
Package settings -> Change visibility -> Public (the repo is public, there are no secrets in the images,
and the VPS can then pull without logging in). Check from the VPS:

```bash
docker pull ghcr.io/pradadipa/dashboard-backend:latest
```

**3. Create a deploy key** (a dedicated key, not your personal one). On your laptop:

```bash
ssh-keygen -t ed25519 -f ~/.ssh/dashboard_deploy -C "github-actions-deploy" -N ""
ssh-copy-id -i ~/.ssh/dashboard_deploy.pub <user>@<vps>     # or append the .pub line to ~/.ssh/authorized_keys
ssh -i ~/.ssh/dashboard_deploy <user>@<vps> 'docker ps'      # must work without a password
```

The user must own the `dashboard` folder and be in the `docker` group (see `docs/deploy-vps.md`).
Being in the `docker` group is root-equivalent, so treat this key like a root key.

**4. Record the server's host key**, so the workflow can refuse a fake server:

```bash
ssh-keyscan -t ed25519 <vps-host>                  # copy the whole output line
# compare its fingerprint with the real one, run ON the VPS:
ssh-keygen -lf /etc/ssh/ssh_host_ed25519_key.pub
```

**5. Create the GitHub environment.** Settings -> Environments -> New environment -> `production`, then add
these secrets to *that environment*:

| Secret | Value |
|---|---|
| `VPS_HOST` | IP or hostname of the VPS |
| `VPS_USER` | the SSH user from step 3 |
| `VPS_SSH_KEY` | the full content of `~/.ssh/dashboard_deploy` (the private key, including the BEGIN/END lines) |
| `VPS_KNOWN_HOSTS` | the line from step 4 |
| `VPS_APP_DIR` | optional, folder of the clone as seen from the SSH home (default `dashboard`) |
| `VPS_PORT` | optional, default `22` |

Optional: tick "Required reviewers" on the environment and every deployment waits for your approval.

## Deploying

Actions -> Deploy -> Run workflow -> keep `latest` -> Run. The script:

1. `git pull --ff-only` (compose files and `db/` scripts)
2. `docker compose pull backend frontend` using `docker-compose.prod.yml`
3. restarts **only** backend and frontend (`--no-deps`, so the database container is never touched)
4. waits for the backend healthcheck, then requests `/` and `/api/annotations` through the frontend nginx

The backend container runs `alembic upgrade head` on start, so migrations are applied automatically.

## Rolling back

Every image is also tagged with its commit, e.g. `sha-1a2b3c4` (shown in the Docker Images run, and in the
package page). Run Deploy again with that tag. Alembic migrations are not undone by a rollback.

## What deploying does NOT do

- **The database and its data are never touched.** `demo.sql.gz` is still restored by hand
  (`docs/deploy-vps.md`).
- **Changes to `db/schema.sql` are not applied automatically.** The deploy updates the file on the server,
  but the views and tables in the running database stay as they were. Apply them yourself:

  ```bash
  docker compose exec -T db psql -U dashboard -d dashboard_demo -v ON_ERROR_STOP=1 -f /db/schema.sql
  ```

  The file is written to be re-runnable, but try it on a copy of the data first.
- Host nginx and certbot are not managed by CD.

The old manual way still works if Actions is down: `git pull && docker compose up -d --build`.
