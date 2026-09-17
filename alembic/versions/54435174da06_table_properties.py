"""Table properties: the registry of a source table's properties

Revision ID: 54435174da06
Revises: 60068ee10c40
Create Date: 2026-09-17

Feature 2 of docs/formshare_case_management/: a property is a typed column of
<table>_properties, a table FormShare creates beside the source table in the
repository, 1:1 on rowuuid. This is the registry row that names it, records
the type inherited from the source variable, and the variable that fills it
when the row is born. The repository table itself is DDL run when the first
property is defined, outside the RSTools contract.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "54435174da06"
down_revision = "60068ee10c40"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "tableproperty",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("form_id", sa.Unicode(length=120), nullable=False),
        sa.Column("table_name", sa.Unicode(length=120), nullable=False),
        sa.Column("property_name", sa.Unicode(length=120), nullable=False),
        sa.Column("property_type", sa.Unicode(length=64), nullable=False),
        sa.Column(
            "property_size", sa.Integer(), server_default=sa.text("'0'"), nullable=True
        ),
        sa.Column(
            "property_decsize",
            sa.Integer(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
        sa.Column("property_desc", sa.Unicode(length=500), nullable=True),
        sa.Column("property_source", sa.Unicode(length=120), nullable=True),
        sa.Column("property_cdate", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            name=op.f("fk_tableproperty_form_id_odkform"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "project_id",
            "form_id",
            "table_name",
            "property_name",
            name=op.f("pk_tableproperty"),
        ),
        mysql_charset="utf8mb4",
        mysql_collate="utf8mb4_unicode_ci",
        mysql_engine="InnoDB",
    )


def downgrade():
    op.drop_table("tableproperty")
