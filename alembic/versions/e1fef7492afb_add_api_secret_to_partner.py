"""Add API secret to partner

Revision ID: e1fef7492afb
Revises: 686cb9908468
Create Date: 2022-11-11 18:44:38.716044

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "e1fef7492afb"
down_revision = "686cb9908468"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "partner",
        sa.Column(
            "partner_apisecret",
            mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"),
            nullable=True,
        ),
    )


def downgrade():
    op.drop_column("partner", "partner_apisecret")
