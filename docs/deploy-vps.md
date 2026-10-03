# Deploy demo to a VPS with a domain

```
internet -> host nginx (80/443, TLS via certbot) -> 127.0.0.1:8080
         -> compose frontend (nginx: static files + read-only /api proxy) -> FastAPI -> Postgres 16
```

The compose stack is unchanged from local use; only `HTTP_PORT` binds the frontend to localhost so the
host nginx is the single public entry point. Postgres is never published.

Real data must never leave your laptop: anonymize locally, ship only the anonymized dump.

## 1. Build the anonymized dump (local machine)

```bash
cp .env.example .env            # set POSTGRES_PASSWORD
docker compose up -d db         # DB is named dashboard_demo (required by the script)

# copy real data into the LOCAL docker volume
# (if pg_dump fails on sequence privileges, use db/copy_real_data.sh instead)
pg_dump "$REAL_DATABASE_URL" | docker compose exec -T db psql -U dashboard -d dashboard_demo

# anonymize (see header of db/anonymize_demo.sql for the options)
docker compose exec -T db psql -U dashboard -d dashboard_demo \
  -v k=0.68 -v salt=<private> -v brand='brand|company' -f /db/anonymize_demo.sql

# optional: break the 1:1 fingerprint with the real data (see header of db/perturb_demo.sql)
docker compose exec -T db psql -U dashboard -d dashboard_demo \
  -v salt=<another-private> -f /db/perturb_demo.sql

docker compose exec -T db pg_dump -U dashboard dashboard_demo | gzip > demo.sql.gz

docker compose down -v          # destroys the local volume that held real data
```

Check the result in a browser before shipping (`docker compose up -d --build`, open http://localhost).
Create your demo login in `auth.users` if you need one; the script empties that table.

## 2. DNS

At your domain registrar, add an `A` record pointing the (sub)domain to the VPS public IP
(and `AAAA` for IPv6 if the VPS has one). Wait until `ping <domain>` resolves to the VPS
before running certbot.

## 3. VPS (Ubuntu 22.04+ / Debian 12, 1 GB RAM minimum, 2 GB recommended for the frontend build)

```bash
sudo apt update && sudo apt install -y nginx certbot python3-certbot-nginx git
curl -fsSL https://get.docker.com | sudo sh && sudo usermod -aG docker $USER   # log out and back in

# firewall: only SSH + HTTP(S). Docker-published ports bypass ufw, which is why
# HTTP_PORT below binds to 127.0.0.1 only.
sudo ufw allow OpenSSH && sudo ufw allow 'Nginx Full' && sudo ufw enable
```

### App stack

```bash
git clone <your-repo> dashboard && cd dashboard
cp .env.example .env && nano .env
#   POSTGRES_PASSWORD=<long random string>   (openssl rand -hex 32)
#   HTTP_PORT=127.0.0.1:8080
# from your laptop:  scp demo.sql.gz <user>@<vps>:~/dashboard/

docker compose up -d db                  # starts only the database
gunzip -c demo.sql.gz | docker compose exec -T db psql -U dashboard -d dashboard_demo
docker compose up -d --build             # backend runs `alembic upgrade head` on start
curl -I http://127.0.0.1:8080            # expect 200
```

Restore before starting the backend, otherwise its migration creates `annotations` first and the restore reports "already exists".

### Host nginx + HTTPS

```bash
sudo cp deploy/nginx/dashboard.conf /etc/nginx/sites-available/dashboard
sudo sed -i 's/dashboard.example.com/<your-domain>/' /etc/nginx/sites-available/dashboard
sudo ln -s /etc/nginx/sites-available/dashboard /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t && sudo systemctl reload nginx

sudo certbot --nginx -d <your-domain> --redirect -m <your-email> --agree-tos
sudo certbot renew --dry-run             # renewal runs from a systemd timer
```

Open https://&lt;your-domain&gt;.

## Notes

- API is read-only through the frontend nginx (`limit_except` in `frontend/nginx.conf`); FastAPI `/docs` is not exposed.
- Update: `git pull && docker compose up -d --build`.
- Logs: `docker compose logs -f backend`, `sudo tail -f /var/log/nginx/error.log`.
- Backup: `docker compose exec -T db pg_dump -U dashboard dashboard_demo | gzip > backup-$(date +%F).sql.gz`.
- 1 GB RAM VPS: running the stack is fine; only the image build is memory-hungry.
  - Add 2 GB swap before the first build: `sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile && echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab`
  - Build one image at a time instead of in parallel: `docker compose build backend && docker compose build frontend && docker compose up -d`
  - Reclaim disk after builds: `docker builder prune -f && docker image prune -f`
  - Cap container logs in `/etc/docker/daemon.json` (`{"log-driver":"json-file","log-opts":{"max-size":"10m","max-file":"3"}}`, then `sudo systemctl restart docker`).
