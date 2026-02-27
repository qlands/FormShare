"""Add cookie consent tables

Revision ID: c1a2b3d4e5f6
Revises: b3711f9c82a0
Create Date: 2026-02-27 00:00:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1a2b3d4e5f6"
down_revision = "b3711f9c82a0"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "cookieconsent",
        sa.Column("consent_id", sa.Unicode(length=64), nullable=False),
        sa.Column("consent_ip", sa.Unicode(length=45), nullable=True),
        sa.Column("consent_cdate", sa.DateTime(), nullable=True),
        sa.Column("consent_udate", sa.DateTime(), nullable=True),
        sa.Column("consent_essential", sa.INTEGER(), nullable=True),
        sa.Column("consent_functional", sa.INTEGER(), nullable=True),
        sa.Column("consent_analytical", sa.INTEGER(), nullable=True),
        sa.Column("consent_marketing", sa.INTEGER(), nullable=True),
        sa.PrimaryKeyConstraint("consent_id"),
    )
    op.create_index(
        op.f("ix_cookieconsent_consent_ip"),
        "cookieconsent",
        ["consent_ip"],
        unique=False,
    )
    op.create_table(
        "cookieconsentlog",
        sa.Column("log_id", sa.Unicode(length=64), nullable=False),
        sa.Column("log_ip", sa.Unicode(length=45), nullable=True),
        sa.Column("log_date", sa.DateTime(), nullable=True),
        sa.Column("log_action", sa.Unicode(length=20), nullable=True),
        sa.Column("log_essential", sa.INTEGER(), nullable=True),
        sa.Column("log_functional", sa.INTEGER(), nullable=True),
        sa.Column("log_analytical", sa.INTEGER(), nullable=True),
        sa.Column("log_marketing", sa.INTEGER(), nullable=True),
        sa.PrimaryKeyConstraint("log_id"),
    )


def downgrade():
    op.drop_table("cookieconsentlog")
    op.drop_table("cookieconsent")
