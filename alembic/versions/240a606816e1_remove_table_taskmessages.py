"""Remove table taskmessages

Revision ID: 240a606816e1
Revises: 4adc5944c025
Create Date: 2021-07-31 09:39:15.389760

"""
import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "240a606816e1"
down_revision = "4adc5944c025"
branch_labels = None
depends_on = None


def upgrade():
    op.drop_table("taskmessages")


def downgrade():
    op.create_table(
        "taskmessages",
        sa.Column("message_id", sa.Unicode(length=64), nullable=False),
        sa.Column("celery_taskid", sa.Unicode(length=64), nullable=False),
        sa.Column("message_date", sa.DateTime(), nullable=True),
        sa.Column("message_content", sa.UnicodeText(), nullable=True),
        sa.ForeignKeyConstraint(
            ["celery_taskid"],
            ["product.celery_taskid"],
            name=op.f("fk_taskmessages_celery_taskid_product"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("message_id", name=op.f("pk_taskmessages")),
        mysql_charset="utf8",
        mysql_engine="InnoDB",
    )
