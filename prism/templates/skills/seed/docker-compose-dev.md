---
skill_id: docker-compose-dev
type: skill
domain_tags: [docker, docker-compose, devops, local-dev, containers]
scope: global
stack_context: [docker, nodejs, python, postgres, redis]
created: 2026-02-20
last_used: 2026-02-20
reuse_count: 0
project_origin: prism-seed
status: active
verified_by: human
---

# Docker Compose for Local Development

## Key Insight
Use named volumes for databases (survives `docker compose down`), anonymous volumes for `node_modules` inside containers, and bind mounts for source code (enables hot reload).

## Trigger
When setting up a local dev environment with multiple services (app + DB + cache).

## Solution

```yaml
# docker-compose.yml
services:
  app:
    build: .
    ports: ["3000:3000"]
    volumes:
      - .:/app                    # source code bind mount (hot reload)
      - /app/node_modules         # anonymous volume — keeps container's node_modules
    environment:
      DATABASE_URL: postgres://user:pass@db:5432/mydb
    depends_on:
      db:
        condition: service_healthy

  db:
    image: postgres:16-alpine
    volumes:
      - db-data:/var/lib/postgresql/data  # named volume — persists data
    environment:
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
      POSTGRES_DB: mydb
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U user -d mydb"]
      interval: 5s
      retries: 5

volumes:
  db-data:
```

## Notes
- `depends_on: condition: service_healthy` waits for DB to be ready before app starts
- Use `.env` file + `env_file: .env` for secrets (add `.env` to `.gitignore`)
- `docker compose watch` (v2.22+) provides smarter file watching than bind mounts
- For Python: no `node_modules` trick needed — use a venv inside container or install to `/app`
