"""Add new partner table

Revision ID: 4895ab4ba318
Revises: 240a606816e1
Create Date: 2021-08-15 09:18:37.409670

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "4895ab4ba318"
down_revision = "240a606816e1"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partner",
        sa.Column(
            "partner_id",
            sa.Unicode(length=64, collation="utf8mb4_unicode_ci"),
            nullable=False,
        ),
        sa.Column("partner_email", sa.Unicode(length=320), nullable=False),
        sa.Column("partner_name", sa.Unicode(length=120), nullable=True),
        sa.Column("partner_organization", sa.Unicode(length=120), nullable=True),
        sa.Column(
            "partner_password",
            mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"),
            nullable=True,
        ),
        sa.Column("partner_cdate", sa.DateTime(), nullable=True),
        sa.Column("partner_telephone", sa.Unicode(length=120), nullable=True),
        sa.Column("partner_apikey", sa.Unicode(length=64), nullable=True),
        sa.Column(
            "created_by",
            sa.Unicode(length=120, collation="utf8mb4_unicode_ci"),
            nullable=False,
        ),
        sa.Column(
            "extras", mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
        sa.Column(
            "tags", mysql.MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["fsuser.user_id"],
            name=op.f("fk_partner_created_by_fsuser"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("partner_id", name=op.f("pk_partner")),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
        mysql_collate="utf8mb4_unicode_ci",
    )


def downgrade():
    op.drop_table("partner")
