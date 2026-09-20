# Deploy demo to a GCP VM

Stack: nginx (static frontend + `/api` proxy, read-only) -> FastAPI -> Postgres 16, all in `docker-compose.yml`. Only port 80 is published.

Real data must never leave your laptop: anonymize locally, ship only the anonymized dump.

## 1. Build the anonymized dump (local machine)

```bash
cp .env.example .env            # set POSTGRES_PASSWORD
docker compose up -d db         # DB is named dashboard_demo (required by the script)

# copy real data into the LOCAL docker volume
pg_dump "$REAL_DATABASE_URL" | docker compose exec -T db psql -U dashboard -d dashboard_demo

# anonymize (see header of db/anonymize_demo.sql for the options)
docker compose exec -T db psql -U dashboard -d dashboard_demo \
  -v k=0.68 -v salt=<private> -v brand='brand|company' -f /db/anonymize_demo.sql

docker compose exec -T db pg_dump -U dashboard dashboard_demo | gzip > demo.sql.gz

docker compose down -v          # destroys the local volume that held real data
```

Check the result in a browser before shipping (`docker compose up -d --build`, open http://localhost).
Create your demo login in `auth.users` if you need one; the script empties that table.

## 2. VM (Ubuntu 22.04+, e2-small or larger)

- Firewall: allow tcp:80 (and 443 if you add TLS). Do not open 5432.
- Install Docker: `curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER`

```bash
git clone <your-repo> dashboard && cd dashboard
cp .env.example .env && nano .env        # strong POSTGRES_PASSWORD
# from your laptop:  scp demo.sql.gz <vm>:~/dashboard/

docker compose up -d db                  # starts only the database
gunzip -c demo.sql.gz | docker compose exec -T db psql -U dashboard -d dashboard_demo
docker compose up -d --build             # backend runs `alembic upgrade head` on start
```

Restore before starting the backend, otherwise its migration creates `annotations` first and the restore reports "already exists".

## Notes

- API is read-only through nginx (`limit_except` in `frontend/nginx.conf`); FastAPI `/docs` is not exposed.
- Update: `git pull && docker compose up -d --build`.
- Logs: `docker compose logs -f backend`.
- HTTPS: put Caddy or a Cloudflare proxy in front, or add a certbot sidecar; not included here.
