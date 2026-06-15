"""add round_of_32 to matchstage enum

Revision ID: b2c3d4e5f601
Revises: 41af6e00a200
Create Date: 2026-06-14

2026 新制：小組賽後為 32 強淘汰。為 matchstage enum 新增 'round_of_32'。
PostgreSQL 需 ALTER TYPE（PG 12+ 可於交易內執行）；SQLite 以 VARCHAR 儲存
enum 且未建 CHECK 約束，無需 schema 變更。
"""
from alembic import op

revision = "b2c3d4e5f601"
down_revision = "41af6e00a200"
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE matchstage ADD VALUE IF NOT EXISTS 'round_of_32'")
    # SQLite / 其他：無原生 enum，無需變更


def downgrade():
    # PostgreSQL 不支援移除 enum 值；保留為 no-op。
    pass
