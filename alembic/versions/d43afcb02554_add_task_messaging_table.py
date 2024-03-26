"""Add task messaging table

Revision ID: d43afcb02554
Revises: 64a5d23f7ce0
Create Date: 2019-04-02 22:04:34.007701

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.mysql import TIMESTAMP

# revision identifiers, used by Alembic.
revision = "d43afcb02554"
down_revision = "64a5d23f7ce0"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    bind = op.get_bind()
    if bind.dialect.name == "mysql":
        op.create_table(
            "taskmessages",
            sa.Column("message_id", sa.Unicode(length=64), nullable=False),
            sa.Column("celery_taskid", sa.Unicode(length=64), nullable=False),
            sa.Column("message_date", TIMESTAMP(fsp=6), nullable=True),
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
    else:
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
        )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("taskmessages")
    # ### end Alembic commands ###
