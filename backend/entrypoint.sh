#!/bin/sh
set -e

# 建立資料表（MVP 用 create_all；正式環境可改 `flask db upgrade` 走 migration）
echo "Initializing database schema..."
python -c "from app import create_app; from app.extensions import db; \
app=create_app('production'); ctx=app.app_context(); ctx.push(); db.create_all()"

# 排程器以行程內 BackgroundScheduler 實作 → 僅單一 worker 避免重複結算。
# 如需多 worker，請關閉 SCHEDULER_ENABLED 並改用獨立排程服務 / 外部 cron。
WORKERS="${GUNICORN_WORKERS:-1}"
echo "Starting gunicorn with ${WORKERS} worker(s)..."
exec gunicorn -w "${WORKERS}" -b 0.0.0.0:5001 --timeout 120 run:app
