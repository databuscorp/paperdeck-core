#!/usr/bin/env bash
# Container entrypoint: migrate, then serve.
#
# `set -e` matters here. If migrations fail we must NOT fall through to gunicorn and
# start serving traffic against a schema the code doesn't match — the container should
# crash-loop visibly instead.
set -euo pipefail

echo "==> Running database migrations"
python /app/scripts/migrate.py

# Azure App Service (and Cloud Run / Heroku) tell the container which port to listen on
# via $PORT and health-probe exactly that port. Hardcoding 8000 makes the platform probe
# a dead port and serve 502s. Default to 8000 for local/docker-compose.
PORT="${PORT:-8000}"
echo "==> Starting gunicorn on 0.0.0.0:${PORT}"

# exec so gunicorn becomes PID 1 and receives SIGTERM directly — otherwise the platform's
# shutdown signal never reaches it and it gets SIGKILLed after the grace period.
#
# Generation jobs run on background threads inside these workers. Two consequences:
#   * "Always On" must be enabled, or an idle unload kills jobs mid-run.
#   * --timeout is a *request* timeout; it does not kill a background thread. Jobs that
#     die with their worker anyway (restart/redeploy/scale-in) are reaped by
#     jobservice.reap_stale_jobs().
exec gunicorn paperdeck.wsgi:application \
    --bind "0.0.0.0:${PORT}" \
    --workers "${GUNICORN_WORKERS:-3}" \
    --timeout "${GUNICORN_TIMEOUT:-120}" \
    --graceful-timeout 30 \
    --access-logfile - \
    --error-logfile -
