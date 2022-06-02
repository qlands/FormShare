"""Partner access by form

Revision ID: f38bbf5ab703
Revises: d350524bfb8a
Create Date: 2021-08-15 15:00:28.647292

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f38bbf5ab703"
down_revision = "d350524bfb8a"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "partnerform",
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
        sa.Column(
            "form_id",
            sa.Unicode(length=120, collation="utf8mb4_unicode_ci"),
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
            name=op.f("fk_partnerform_granted_by_fsuser"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["partner_id"],
            ["partner.partner_id"],
            name=op.f("fk_partnerform_partner_id_partner"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            name=op.f("fk_partnerform_project_id_odkform"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "partner_id", "project_id", "form_id", name=op.f("pk_partnerform")
        ),
        mysql_charset="utf8mb4",
        mysql_engine="InnoDB",
        mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index(
        "fk_partnerform_form1_idx",
        "partnerform",
        ["project_id", "form_id"],
        unique=False,
    )


def downgrade():
    op.drop_table("partnerform")
