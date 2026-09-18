# LabBoard

LabBoard is a small, production-conscious announcement board for one administrator. It
uses FastAPI, SQLAlchemy/SQLite, filesystem attachments, and Server-Sent Events (SSE).
The frontend is deliberately plain and neutral so it is usable as a lab, class, or team
notice board.

## Run without Docker

Python 3.14 and [uv](https://docs.astral.sh/uv/) are recommended:

```bash
cp .env.example .env
# Edit .env and replace ADMIN_PASSWORD with a strong password.
# Set PUBLIC_BASE_URL to the URL users use to open the app.
uv sync --dev
uv run uvicorn labboard.app:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000>. The public announcement page is available at `/`.
The administrator login page is available at `/admin/login`; after signing in,
publishing is available at `/admin`.

The first startup creates the SQLite schema, upload directory, and a random JWT signing
secret at `./data/.jwt_secret`. The secret is reused across restarts and is excluded
from version control. `ADMIN_PASSWORD` must be at least 12 characters; the application
fails fast otherwise.

`PUBLIC_BASE_URL` controls the absolute URLs returned for attachment downloads. For
Docker on a LAN, set it to the host address and published port, for example
`http://172.16.11.217:8080`.

Stop the development server with `Ctrl+C`.

## Run with Docker Compose

The production-shaped deployment serves the static frontend through nginx and proxies
`/api/` and `/events` to one backend process:

```bash
cp .env.example .env
# Edit .env and replace ADMIN_PASSWORD with a strong password.
docker compose --env-file .env up --build -d
```

Open <http://127.0.0.1:8080>. The public announcement page is available at `/`.
The administrator login page is available at `/admin/login`; after signing in,
publishing is available at `/admin`.

`db-data` and `uploads` are named persistent volumes. Both containers run as non-root
users. Compose keeps one lightweight backend readiness check, running once per minute
for startup ordering; duplicate image and frontend probes are intentionally disabled.
Keep `COOKIE_SECURE=true` when TLS is terminated at a trusted reverse proxy; local HTTP
development uses `false`.

Useful Compose commands:

```bash
# Show service status
docker compose --env-file .env ps

# Follow all logs
docker compose --env-file .env logs -f

# Stop containers and preserve database/uploads
docker compose --env-file .env down

# Rebuild after code changes
docker compose --env-file .env up --build -d
```

Compose automatically reads `.env` from the project directory, so `--env-file .env`
may be omitted when using that filename:

```bash
docker compose up --build -d
```

To use a different environment file:

```bash
docker compose --env-file .env.production up --build -d
```

The public page does not expose an admin login control. Open
<http://127.0.0.1:8080/admin/login> to use the separate administrator login page.
Successful authentication redirects to <http://127.0.0.1:8080/admin>.
The `Enable notifications` control uses the browser Notification API for live tabs. It
does not provide notifications after the browser is closed; that requires a separate
HTTPS Web Push/VAPID service.

## Using the application

Public viewers can read announcements, open links, download attachments, and receive
live updates while the page is open. To publish, open `/admin/login`, enter the single
administrator password, and create an announcement with optional links and multiple
attachments. No account creation or password-reset flow is provided.

## Security model

* There is exactly one administrator. Its password is seeded from `ADMIN_PASSWORD`;
  there is intentionally no account creation, password reset, or user-management API.
* Passwords are hashed with Argon2id via `pwdlib`. Login issues a short-lived JWT in a
  Secure/HttpOnly/SameSite cookie. A separate CSRF cookie plus `X-CSRF-Token` header
  protects every state-changing authenticated request.
* Login is rate limited in memory per client IP. Security headers, generic server errors,
  strict upload extension/size/count limits, generated storage names, and download-only
  attachment responses are enabled by default.
* Uploads are kept outside the static frontend and are never served by path. ORM
  statements are parameterized SQLAlchemy queries.

For internet-facing use, put the nginx frontend behind HTTPS, use a strong password
from a secret manager, restrict the host with a firewall, and monitor logs. Protect the
database volume because it contains the generated JWT signing secret; deleting it
logs out all sessions and generates a new signing key.
The in-memory limiter is per process and is intentionally simple; use a shared gateway
or Redis before running multiple instances.

## Data and backup

SQLite is stored in `DATABASE_URL` (the Docker database volume maps to `/app/data`) and
attachments in `UPLOAD_DIR` (the Docker uploads volume maps to `/app/uploads`). Back up
the database and uploads together, preferably while the service is stopped or after a
SQLite-consistent snapshot. Restoring only one of the two can leave attachment records
without files.

## SSE and scaling

The backend starts one in-process event broker. nginx disables buffering and keeps the
`/events` connection open with heartbeats. A reconnect sends a `refetch` event, so the
browser reloads the authoritative announcement list and does not depend on an event
history. Subscriber queues are bounded; slow clients are dropped and reconnect safely.

Run one backend worker initially. Multiple workers do not share the broker, so live
updates are not broadcast across workers; Redis or another shared broker is deferred.
SSE only updates browser tabs that are open. It is not push delivery to a closed browser
and does not replace email, mobile push, or a notification service.

## Tests

```bash
uv run pytest -q
```

The focused suite covers startup/health, authentication and CSRF, attachment
validation/downloads, event reconnect behavior, and a 150-subscriber bounded SSE
concurrency check.
