"""create estimates table

Revision ID: 001
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "estimates",
        sa.Column("estimate_id", sa.String(36), primary_key=True, nullable=False),
        sa.Column("client_id", sa.String(128), nullable=False),
        sa.Column("vehicle_vin", sa.String(17), nullable=False),
        sa.Column("vehicle_year", sa.Integer(), nullable=False),
        sa.Column("vehicle_make", sa.String(64), nullable=False),
        sa.Column("vehicle_model", sa.String(64), nullable=False),
        sa.Column("damage_description", sa.Text(), nullable=False),
        sa.Column("photo_urls", sa.JSON(), nullable=False),
        sa.Column("office_ids", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending", "processing", "completed", "failed",
                name="estimate_status",
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("estimated_total_usd", sa.Float(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # Individual column indexes
    op.create_index("ix_estimates_client_id", "estimates", ["client_id"])
    op.create_index("ix_estimates_vehicle_vin", "estimates", ["vehicle_vin"])
    op.create_index("ix_estimates_status", "estimates", ["status"])

    # Composite index for common query pattern: filter by client + status
    op.create_index("ix_estimates_client_status", "estimates", ["client_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_estimates_client_status", table_name="estimates")
    op.drop_index("ix_estimates_status", table_name="estimates")
    op.drop_index("ix_estimates_vehicle_vin", table_name="estimates")
    op.drop_index("ix_estimates_client_id", table_name="estimates")
    op.drop_table("estimates")

    # Drop the Postgres enum type (no-op on SQLite)
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        sa.Enum(name="estimate_status").drop(bind, checkfirst=True)
