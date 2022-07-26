"""Remove separate table

Revision ID: 27849ecf5d0b
Revises: d79b5450910f
Create Date: 2019-08-31 23:43:10.867276

"""
import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = "27849ecf5d0b"
down_revision = "d79b5450910f"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("septable")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "septable",
        sa.Column("project_id", mysql.VARCHAR(length=64), nullable=False),
        sa.Column("form_id", mysql.VARCHAR(length=120), nullable=False),
        sa.Column("table_name", mysql.VARCHAR(length=120), nullable=False),
        sa.Column("table_desc", mysql.TEXT(), nullable=True),
        sa.ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            name="fk_septable_project_id_odkform",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("project_id", "form_id", "table_name"),
        mysql_default_charset="utf8",
        mysql_engine="InnoDB",
    )
    # ### end Alembic commands ###