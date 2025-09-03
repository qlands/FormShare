"""Disconnect collaborator from project

Revision ID: e11efc4fc945
Revises: e9bf944eff96
Create Date: 2025-08-25 10:00:26.952588

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e11efc4fc945"
down_revision = "e9bf944eff96"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "fk_collaborator_project_id_project", "collaborator", type_="foreignkey"
    )
    op.execute("SET sql_generate_invisible_primary_key=OFF")
    op.execute("ALTER TABLE collaborator DROP PRIMARY KEY")
    op.execute("SET sql_generate_invisible_primary_key=ON")


def downgrade():
    op.create_foreign_key(
        "fk_collaborator_project_id_project",
        "collaborator",
        "project",
        ["project_id"],
        ["project_id"],
        ondelete="CASCADE",
    )
    op.create_primary_key(
        op.f("pk_collaborator"),
        "collaborator",
        ["project_id", "coll_id"],
    )
