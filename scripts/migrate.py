#!/usr/bin/env python
"""Run Django migrations safely at container start.

App Service can start several instances at once (scale-out, or a rolling restart), and
each one boots this container. Django does not lock `django_migrations`, so two
instances migrating simultaneously can race — applying the same DDL twice, deadlocking,
or leaving the table half-written. On Postgres we therefore take a session-level
advisory lock first: the first instance migrates, the others block, then find nothing
to do and continue. On SQLite (local dev) there is no such contention, so we just run.

Exits non-zero on failure. That is deliberate: the container must crash-loop loudly
rather than come up and serve traffic against a schema it doesn't match.
"""
import os
import pathlib
import sys

# Running a script from inside scripts/ puts scripts/ on sys.path — not the project
# root — so `import paperdeck.settings` would fail. Put the repo root first.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

import django  # noqa: E402  (must follow the sys.path fix above)

# Arbitrary but fixed application-wide lock id. Every instance of this app uses the same
# one, which is exactly the point — they must serialize against each other.
MIGRATION_LOCK_ID = 4820_1379


def main() -> int:
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "paperdeck.settings")
    django.setup()

    from django.core.management import call_command
    from django.db import connection

    is_postgres = connection.vendor == "postgresql"

    if not is_postgres:
        print("migrate: sqlite — running without an advisory lock", flush=True)
        call_command("migrate", interactive=False, verbosity=1)
        return 0

    print(f"migrate: acquiring advisory lock {MIGRATION_LOCK_ID}…", flush=True)
    with connection.cursor() as cur:
        # Blocks until we get it — a peer instance may be migrating right now.
        cur.execute("SELECT pg_advisory_lock(%s)", [MIGRATION_LOCK_ID])
    try:
        call_command("migrate", interactive=False, verbosity=1)
    finally:
        with connection.cursor() as cur:
            cur.execute("SELECT pg_advisory_unlock(%s)", [MIGRATION_LOCK_ID])
        print("migrate: released advisory lock", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
