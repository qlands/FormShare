"""New table case lookup

Revision ID: 01b3430ed67e
Revises: cc445e8657bf
Create Date: 2021-03-21 14:10:17.665380

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "01b3430ed67e"
down_revision = "cc445e8657bf"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "caselookup",
        sa.Column("project_id", sa.Unicode(length=64), nullable=False),
        sa.Column("field_name", sa.Unicode(length=120), nullable=False),
        sa.Column("field_as", sa.Unicode(length=45), nullable=True),
        sa.Column(
            "field_editable", sa.INTEGER(), server_default=sa.text("'1'"), nullable=True
        ),
        sa.ForeignKeyConstraint(
            ["project_id"],
            ["project.project_id"],
            name=op.f("fk_caselookup_project_id_project"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id", "field_name", name=op.f("pk_caselookup")),
        mysql_charset="utf8",
        mysql_engine="InnoDB",
    )


def downgrade():
    op.drop_table("caselookup")
