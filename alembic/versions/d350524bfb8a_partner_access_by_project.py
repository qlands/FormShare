"""Partner access by project

Revision ID: d350524bfb8a
Revises: 9aefe68f8d78
Create Date: 2021-08-15 14:42:13.321568

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "d350524bfb8a"
down_revision = "9aefe68f8d78"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partnerproject",
        sa.Column(
            "partner_id",
            sa.Unicode(length=64, collation="utf8mb4_unicode_ci"),
            nullable=False,
        ),
        sa.Column(
            "project_id",
            sa.Unicode(length=64, collation="utf8mb4_unicode_ci"),
            nullable=False,
        ),
        sa.Column("access_date", sa.DateTime(), nullable=True),
        sa.Column(
            "granted_by",
            sa.Unicode(length=120, collation="utf8mb4_unicode_ci"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["fsuser.user_id"],
            name=op.f("fk_partnerproject_granted_by_fsuser"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partner.partner_id"],
            name=op.f("fk_partnerproject_partner_id_partner"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name=op.f("fk_partnerproject_project_id_project"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "partner_id", "project_id", name=op.f("pk_partnerproject")
        ),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        op.f("ix_partnerproject_project_id"),
        "partnerproject",
        ["project_id"],
        unique=False,
    )


def downgrade():
    op.drop_table("partnerproject")
