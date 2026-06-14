#!/bin/sh
set -e

# 套用資料庫 migration（Alembic / Flask-Migrate）。冪等：已是最新則不動作。
echo "Applying database migrations..."
export FLASK_APP=run.py
flask db upgrade

# 排程器以行程內 BackgroundScheduler 實作 → 僅單一 worker 避免重複結算。
# 如需多 worker，請關閉 SCHEDULER_ENABLED 並改用獨立排程服務 / 外部 cron。
WORKERS="${GUNICORN_WORKERS:-1}"
echo "Starting gunicorn with ${WORKERS} worker(s)..."
exec gunicorn -w "${WORKERS}" -b 0.0.0.0:5001 --timeout 120 run:app
