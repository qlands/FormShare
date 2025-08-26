"""Drop relations of collingroup

Revision ID: 34b3241b325d
Revises: 694bf0fb0f92
Create Date: 2025-08-25 09:05:04.363708

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "34b3241b325d"
down_revision = "694bf0fb0f92"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_constraint(
        "fk_collingroup_enum_project_collaborator", "collingroup", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_collingroup_project_id_collgroup", "collingroup", type_="foreignkey"
    )
    op.drop_index("fk_enumingroup_enumerator1", table_name="collingroup")
    op.drop_index("fk_enumingroup_enumerator1_idx", table_name="collingroup")
    op.execute("ALTER TABLE collingroup DROP PRIMARY KEY")


def downgrade():
    op.create_index(
        "fk_enumingroup_enumerator1_idx",
        "collingroup",
        ["enum_project", "coll_id"],
        unique=False,
    )
    op.create_index(
        "fk_enumingroup_enumerator1",
        "collingroup",
        ["enum_project", "coll_id"],
        unique=False,
    )
    op.create_foreign_key(
        "fk_collingroup_project_id_collgroup",
        "collingroup",
        "collgroup",
        ["project_id", "group_id"],
        ["project_id", "group_id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        "fk_collingroup_enum_project_collaborator",
        "collingroup",
        "collaborator",
        ["enum_project", "coll_id"],
        ["project_id", "coll_id"],
        ondelete="CASCADE",
    )
    op.create_primary_key(
        op.f("pk_collingroup"),
        "collingroup",
        ["project_id", "group_id", "enum_project", "coll_id"],
    )
