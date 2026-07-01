# Local infrastructure

Data-tier services for local development, defined in [`../docker-compose.yml`](../docker-compose.yml):

| Service | Image | Host port | Purpose |
|---------|-------|-----------|---------|
| postgres | `pgvector/pgvector:pg16` | 5432 | Metadata DB + vector store (pgvector) |
| redis | `redis:7-alpine` | 6379 | Ingestion queue + cache |
| minio | `minio/minio` | 9000 (API), 9001 (console) | Object store for raw PDFs + artifacts |
| minio-setup | `minio/mc` | — | One-shot: creates the `akasha-documents` bucket, then exits |

Connection defaults live in [`../.env.example`](../.env.example); copy it to
`.env` to override ports/credentials. Compose reads the same `.env`.

## Bring it up

```powershell
docker compose up -d
docker compose ps            # postgres/redis "healthy"; minio-setup "exited (0)"
```

## Verify

```powershell
# pgvector + extensions enabled
docker exec akasha-postgres psql -U akasha -d akasha_rag -c "\dx"
# expect: citext, pgcrypto, vector

# redis
docker exec akasha-redis redis-cli ping         # -> PONG

# minio bucket
docker run --rm --network akasha-rag_default minio/mc sh -c "mc alias set l http://minio:9000 minioadmin minioadmin && mc ls l"
```

MinIO console: http://localhost:9001 (user/pass `minioadmin` / `minioadmin`).

## Notes

- The Postgres init SQL runs **only on a fresh volume**. After editing
  `infra/postgres/init/*.sql`, recreate the volume: `docker compose down -v && docker compose up -d`.
- Port already in use? Set `POSTGRES_PORT` / `REDIS_PORT` / `MINIO_PORT` in `.env`.
- Named volumes (`pgdata`, `redisdata`, `miniodata`) persist across restarts.

## Tear down

```powershell
docker compose down          # stop, keep data
docker compose down -v       # stop AND wipe volumes (fresh start)
```
