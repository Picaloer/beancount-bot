#!/bin/sh
set -e

echo "[entrypoint] Waiting for PostgreSQL..."
until uv run python -c "
import os, sys
from sqlalchemy import create_engine, text
try:
    e = create_engine(os.environ['DATABASE_URL'])
    with e.connect() as c:
        c.execute(text('SELECT 1'))
    sys.exit(0)
except Exception as ex:
    print(ex, file=sys.stderr)
    sys.exit(1)
" 2>/dev/null; do
    sleep 1
done
echo "[entrypoint] PostgreSQL is ready."

exec "$@"
