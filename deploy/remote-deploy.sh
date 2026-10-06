#!/usr/bin/env bash
# Runs ON THE VPS. .github/workflows/deploy.yml pipes this file through ssh:
#
#   ssh user@vps "bash -s -- <app_dir> <image_tag>" < deploy/remote-deploy.sh
#
# What it does: update the repo files, pull the two application images, restart ONLY backend
# and frontend, and prove the stack works. The database container and its volume are never touched
# (no `down`, no `-v`, `--no-deps`).
set -euo pipefail

app_dir="${1:?usage: remote-deploy.sh <app_dir> [image_tag]}"
tag="${2:-latest}"

# The tag ends up in an image name, so accept nothing exotic.
if [[ ! "$tag" =~ ^[A-Za-z0-9._-]+$ ]]; then
  echo "Invalid image tag: '$tag'" >&2
  exit 2
fi

cd "$app_dir"

echo "==> Updating repo files (compose files, db/ scripts)"
git pull --ff-only

export IMAGE_TAG="$tag"
dc=(docker compose -f docker-compose.yml -f docker-compose.prod.yml)

echo "==> Pulling images (tag: $tag)"
"${dc[@]}" pull backend frontend

echo "==> Restarting backend and frontend (database is NOT touched)"
"${dc[@]}" up -d --no-build --no-deps backend frontend

echo "==> Waiting for the backend healthcheck"
cid="$("${dc[@]}" ps -q backend)"
status="starting"
for _ in $(seq 1 40); do
  status="$(docker inspect -f '{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}' "$cid")"
  [[ "$status" == "healthy" ]] && break
  sleep 3
done
if [[ "$status" != "healthy" ]]; then
  echo "Backend is '$status' after 2 minutes. Last logs:" >&2
  "${dc[@]}" logs --tail 60 backend >&2
  echo "To roll back: run the Deploy workflow again with a previous sha-... tag." >&2
  exit 1
fi

echo "==> End-to-end check: frontend nginx -> backend -> database"
http_port="$(grep -E '^HTTP_PORT=' .env 2>/dev/null | tail -1 | cut -d= -f2- | tr -d "\"'" || true)"
http_port="${http_port:-80}"
if [[ "$http_port" == *:* ]]; then base="http://${http_port}"; else base="http://127.0.0.1:${http_port}"; fi
curl -fsS -o /dev/null --retry 5 --retry-delay 2 --retry-connrefused "${base}/"
curl -fsS -o /dev/null --retry 5 --retry-delay 2 --retry-connrefused "${base}/api/annotations"

docker image prune -f >/dev/null
"${dc[@]}" ps
echo "==> Deployed tag: $tag"
