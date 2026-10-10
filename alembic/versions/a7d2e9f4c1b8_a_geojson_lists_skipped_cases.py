"""How many cases a GeoJSON list's last generation left out

Revision ID: a7d2e9f4c1b8
Revises: f5c8a1e3b7d9
Create Date: 2026-10-07

A published list can be served as GeoJSON (feature 6, stage 5), its features
made by RSTools' caselistgen from a geopoint, geotrace or geoshape column of
the source. A case with no location, or with one that cannot be the geometry
asked for, is left out and counted rather than failing the list.
publishedlist.list_skipped keeps the count of the last generation, so the
lists page can say how many cases are on no map.
"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a7d2e9f4c1b8"
down_revision = "f5c8a1e3b7d9"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "publishedlist", sa.Column("list_skipped", sa.INTEGER(), nullable=True)
    )


def downgrade():
    op.drop_column("publishedlist", "list_skipped")
