# Running the API Test Suite

This guide covers running the Django/pytest suite for `apps/api` inside Docker via `compose-test.yaml` at the repo root. The compose file boots an isolated stack — Postgres, Valkey (Redis), RabbitMQ, S3-compatible storage (`pgsty/silo`) — with tmpfs-backed data dirs, so every run begins from a clean slate and a single teardown command removes everything.

For background on the test layout, markers, and fixtures, see [`TESTING_GUIDE.md`](../plane/tests/TESTING_GUIDE.md) and [`README.md`](../plane/tests/README.md).

## Prerequisites

- Docker and Docker Compose v2 (`docker compose ...`)
- Env files generated via the setup script:

  ```bash
  ./setup.sh
  ```

  This copies `apps/api/.env.example` → `apps/api/.env` (along with the other app env files). The compose file reads `apps/api/.env`, so this step must run **before** the first `docker compose` invocation.

## Running the suite

All commands are run from the repo root.

### Full suite

```bash
docker compose -f compose-test.yaml up \
  --build \
  --abort-on-container-exit \
  --exit-code-from api-tests
```

- `--build` rebuilds the `api-tests` image when `Dockerfile.dev`, `pyproject.toml` or `uv.lock` change.
- `--abort-on-container-exit` stops the dependency services as soon as `api-tests` exits.
- `--exit-code-from api-tests` propagates pytest's exit code so this works in CI.

### Filtered runs

Use `docker compose run` to override the default `pytest` command. Anything you pass after the service name is forwarded to pytest.

```bash
# Only unit tests (marker defined in pytest.ini)
docker compose -f compose-test.yaml run --rm --build api-tests pytest -m unit

# A single directory, filtered by name
docker compose -f compose-test.yaml run --rm --build api-tests \
  pytest plane/tests/unit -k "test_workspace"

# Single file with verbose output
docker compose -f compose-test.yaml run --rm --build api-tests \
  pytest plane/tests/unit/models/test_workspace_model.py -vv
```

The available markers (`unit`, `contract`, `smoke`, `slow`) are declared in `apps/api/pytest.ini`.

### Teardown

```bash
docker compose -f compose-test.yaml down -v
```

`-v` removes the ephemeral volumes and the `test_env` network. Because the data directories are tmpfs, no host state survives a teardown — every run starts clean. Run this between unrelated test sessions to free Docker resources.

## How it works

| Service      | Image                                               | Purpose                                 |
| ------------ | --------------------------------------------------- | --------------------------------------- |
| `test-db`    | `postgres:15.7-alpine`                              | Application database                    |
| `test-redis` | `valkey/valkey:7.2.11-alpine`                       | Cache / Celery broker                   |
| `test-mq`    | `rabbitmq:3.13.6-management-alpine`                 | Task queue                              |
| `test-minio` | `docker.io/pgsty/silo:RELEASE.2026-09-16T00-00-00Z` | S3-compatible object storage            |
| `api-tests`  | built from `apps/api/Dockerfile.dev`                | `uv sync`s the locked deps, runs pytest |

All four dependencies expose health checks; `api-tests` waits for `service_healthy` on each via `depends_on`, so pytest only starts once the stack is ready.

Test-time env overrides live in the compose file itself (`POSTGRES_HOST=test-db`, `REDIS_URL=redis://test-redis:6379/`, `AWS_S3_ENDPOINT_URL=http://test-minio:9000`, `DJANGO_SETTINGS_MODULE=plane.settings.test`). Everything else is inherited from `apps/api/.env`.

## Running in a sandbox with an egress proxy

Cloud/agent sandboxes often block direct internet access and route HTTPS through a proxy that re-signs TLS. Build containers can't reach that proxy or trust its CA, so `docker compose -f compose-test.yaml up --build` fails in `apk add` (`DNS lookup error`) or `uv sync` (`invalid peer certificate: UnknownIssuer`). Normal machines and CI don't need any of this.

Without changing any repo file, keep a patched Dockerfile and a compose override outside the repo and pass both to compose. In the examples, `CA_DIR` is the directory holding the proxy CA bundle (`ca-bundle.crt`) and `WORK` is any scratch directory.

1. **Allow the registries.** The sandbox network policy must allow `ghcr.io` and `pkg-containers.githubusercontent.com` (the `uv` base image) alongside Docker Hub.
2. **Trust the proxy CA in the build.** Create `$WORK/Dockerfile.sandbox` from `apps/api/Dockerfile.dev`, inserting this right after `FROM python:3.12.5-alpine AS backend`:

   ```dockerfile
   COPY --from=ca ca-bundle.crt /usr/local/share/ccr-ca.crt
   RUN cat /usr/local/share/ccr-ca.crt >> /etc/ssl/certs/ca-certificates.crt
   ENV UV_NATIVE_TLS=1 UV_SYSTEM_CERTS=1 SSL_CERT_FILE=/usr/local/share/ccr-ca.crt REQUESTS_CA_BUNDLE=/usr/local/share/ccr-ca.crt CARGO_HTTP_CAINFO=/usr/local/share/ccr-ca.crt
   ARG HTTPS_PROXY
   ARG https_proxy
   ARG NO_PROXY
   ARG no_proxy
   ```

   The `ENV` points at a separate copy of the CA because `apk add` replaces `/etc/ssl/certs/ca-certificates.crt` and would drop the appended CA before `uv sync` runs.

3. **Build on the host network and fix RabbitMQ.** Create `$WORK/compose.override.yaml`:

   ```yaml
   services:
     api-tests:
       build:
         context: ./apps/api
         dockerfile: /abs/path/to/Dockerfile.sandbox
         network: host
         additional_contexts:
           ca: /abs/path/to/CA_DIR
         args:
           HTTPS_PROXY: ${HTTPS_PROXY}
           https_proxy: ${HTTPS_PROXY}
           NO_PROXY: ${NO_PROXY}
           no_proxy: ${NO_PROXY}
     test-mq:
       # The default root-owned tmpfs makes RabbitMQ fail to read .erlang.cookie (eacces)
       tmpfs: !override
         - /var/lib/rabbitmq:uid=100,gid=101,mode=0755
   ```

4. **Run with both files:**

   ```bash
   docker compose -f compose-test.yaml -f "$WORK/compose.override.yaml" \
     up --build --abort-on-container-exit --exit-code-from api-tests
   docker compose -f compose-test.yaml -f "$WORK/compose.override.yaml" down -v
   ```

Host networking gives the build the host's network namespace, so only use this where that is acceptable. If you can't use Docker at all, the suite also runs natively (`cd apps/api && uv sync`, then `pytest`) against a local Postgres and Redis, but tests that dispatch Celery tasks fail without a RabbitMQ broker on `localhost:5672`, and a test database left over from an older checkout can cause `NOT NULL` errors — pass `--create-db`.

## Troubleshooting

- **`./apps/api/.env: no such file or directory`** — run `./setup.sh` from the repo root.
- **Port already in use** — none of the test services publish host ports; if you see this it's coming from a different compose stack. Stop the local stack (`docker compose -f compose-local.yaml down`).
- **Stale image after dependency changes** — rebuild explicitly: `docker compose -f compose-test.yaml build --no-cache api-tests`.
- **S3 bucket missing** — the `test-minio` (`pgsty/silo`) entrypoint creates the bucket named by `AWS_S3_BUCKET_NAME` (default `uploads`). Change the value in `apps/api/.env` and re-run.
- **Database state leaking between runs** — confirm you ran `down -v` (not just `down`). The tmpfs mounts are torn down with the container, but the network and any externally created volumes need `-v` to clear.
