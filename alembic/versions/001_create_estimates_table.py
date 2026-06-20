"""Create estimates table

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
        sa.Column("id", sa.String(36), primary_key=True, nullable=False,
                  comment="UUID v4 — matches the estimate_id returned to clients"),
        sa.Column("client_id", sa.String(128), nullable=False,
                  comment="Unique identifier for the client repair shop"),
        sa.Column("vehicle_vin", sa.String(17), nullable=False,
                  comment="17-character Vehicle Identification Number"),
        sa.Column("vehicle_year", sa.Integer(), nullable=False),
        sa.Column("vehicle_make", sa.String(64), nullable=False),
        sa.Column("vehicle_model", sa.String(64), nullable=False),
        sa.Column("damage_description", sa.Text(), nullable=False),
        sa.Column("photo_urls", sa.Text(), nullable=False, server_default="[]",
                  comment="JSON-encoded list of photo URLs"),
        sa.Column("office_ids", sa.Text(), nullable=False, server_default="[1]",
                  comment="JSON-encoded list of AI office IDs to involve"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending",
                  comment="pending | processing | completed | failed"),
        sa.Column("estimated_total_usd", sa.Float(), nullable=True,
                  comment="Final estimate in USD, populated when status=completed"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    # Indexes for common query patterns
    op.create_index("ix_estimates_client_id", "estimates", ["client_id"])
    op.create_index("ix_estimates_vehicle_vin", "estimates", ["vehicle_vin"])
    op.create_index("ix_estimates_status", "estimates", ["status"])
    op.create_index("ix_estimates_created_at", "estimates", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_estimates_created_at", table_name="estimates")
    op.drop_index("ix_estimates_status", table_name="estimates")
    op.drop_index("ix_estimates_vehicle_vin", table_name="estimates")
    op.drop_index("ix_estimates_client_id", table_name="estimates")
    op.drop_table("estimates")
