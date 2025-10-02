# DayZ HiveAPI – Working Roadmap (Docker-first)

This file captures the current status and the exact next steps so you can resume quickly in a fresh session.

## Current status

- Stack: FastAPI + PostgreSQL (16) + Redis, Prometheus, Grafana, optional Cloudflare Tunnel
- Local orchestration: `hiveapi/ops/docker-compose.yml`
- Implemented APIs:
  - Auth: `POST /v1/auth/server-login`
  - Characters: `POST /v1/characters/claim`, `POST /v1/characters/heartbeat`
  - Inventory: `POST /v1/inventory/set`, `POST /v1/inventory/apply` (checksum + conflict detection)
  - Server stub: `GET /v1/server-stub/ping`, `POST /v1/server-stub/bootstrap`
  - Admin: `GET /v1/admin/overview`, `GET /v1/admin/events`, `GET /v1/admin/events/stream`
  - Health/metrics: `GET /health`, Prometheus scrape enabled
- Entrypoint runs DB migrations and optional seeding on container start.

## Immediate next steps (local Docker + Cloudflare Tunnel)

1) Optional security: generate and export a shared secret for the tunnel

```bash
export ORIGIN_SECRET=$(openssl rand -hex 32)   # optional but recommended
export TUNNEL_TOKEN=<your-cloudflared-token>   # optional; enables built-in tunnel service
```

2) Bring up the stack

```bash
docker compose -f hiveapi/ops/docker-compose.yml up -d --build
```

3) Local smoke checks

```bash
curl http://localhost:8000/health
curl http://localhost:8000/v1/admin/overview
```

4) Tunnel (two options)

- Built-in (recommended): set `TUNNEL_TOKEN` env and the `cloudflared` service in compose will connect automatically.
- Quick dev tunnel (manual):

```bash
cloudflared tunnel --url http://localhost:8000
```

If `ORIGIN_SECRET` is set, ensure your named tunnel injects header:

```
X-Origin-Secret: <your ORIGIN_SECRET>
```

5) Smoke test via the tunnel URL

```bash
curl https://<your-tunnel-host>/health
curl https://<your-tunnel-host>/v1/admin/overview
```

6) End-to-end gameplay flow

```bash
# Create demo data (tenant/server/player)
curl -X POST https://<tunnel>/v1/server-stub/bootstrap -H 'Content-Type: application/json' -d '{}'

# Server login (dev mode if signatures disabled)
curl -X POST https://<tunnel>/v1/auth/server-login -H 'Content-Type: application/json' \
  -d '{"server_id":"demo-server","api_key":"demo-key"}'

# Claim character for a player
curl -X POST https://<tunnel>/v1/characters/claim -H 'Content-Type: application/json' \
  -d '{"steam_id":"76561198000000000","server_id":"demo-server"}'

# Set or apply inventory
curl -X POST https://<tunnel>/v1/inventory/set -H 'Content-Type: application/json' \
  -d '{"character_id":"<id>", "inventory": {"items": ["HockeyStick","BeerCan"]}}'
```

## Near-term backlog (Public Beta pack)

- Rate limiting (per server/IP) using Redis token-bucket
- Onboarding: tenant bootstrap + invite tokens
- Documentation: OpenAPI examples + “Developer Reference” with Enforce examples
- Discord integration (phase 1): OAuth link, roles add/remove, send message to user/channel
- Event replay and richer SSE stream filters
- Postman collection and Makefile targets
- Deployment recipe for VPS + Coolify (optional, alternative to tunnel)

## Parity with DaemonForge Universal API (tracked work)

Implement general-purpose JSON store and ops using Postgres JSONB to emulate Mongo-like API:

- Tables: `db_objects(namespace, key, data jsonb, version, updated_at)`, `db_players(player_id, namespace, data jsonb, ...)`, `db_globals(namespace, data jsonb, ...)`
- Endpoints (player/object/globals variants):
  - save, load, load_json, query (safe subset), update ($set/$unset/$push/$pull), transaction/increment ($inc)
- Query subset mapping to SQL: $eq/$ne/$in/$nin/$gt/$lt/$and/$or
- Atomic ops via single `UPDATE ... RETURNING` with `jsonb_set`, array ops, and numeric casts
- Extend Enforce SDK to wrap these endpoints and return standard status codes

## Optional alternate track (later)

- Supabase (managed Postgres + Edge Functions) and Vercel admin UI; refactor endpoints into functions; use Realtime for events. Nice for scale, not required for MVP.

## Useful paths

- Compose: `hiveapi/ops/docker-compose.yml`
- Dockerfile: `hiveapi/ops/Dockerfile`
- Tunnel sample: `hiveapi/ops/cloudflared/config.yml.sample`
