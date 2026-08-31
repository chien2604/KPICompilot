#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
    mkdir -p /app/storage/uploads /app/storage/kuzu_db /app/storage/imports
    chown -R kpi:kpi /app/storage
    exec gosu kpi "$0" "$@"
fi

attempt=1
maximum_attempts="${DATABASE_WAIT_ATTEMPTS:-30}"

until python -c "from sqlalchemy import text; from db.database import engine; connection = engine.connect(); connection.execute(text('SELECT 1')); connection.close()" >/dev/null 2>&1; do
    if [ "$attempt" -ge "$maximum_attempts" ]; then
        echo "PostgreSQL chưa sẵn sàng sau ${maximum_attempts} lần kiểm tra." >&2
        exit 1
    fi

    echo "Đang chờ PostgreSQL (${attempt}/${maximum_attempts})..."
    attempt=$((attempt + 1))
    sleep 2
done

echo "Khởi tạo schema và áp dụng migration..."
python -m db.init_db

for migration in /app/migrations/[0-9][0-9][0-9]_*.py; do
    python "$migration"
done

exec "$@"

