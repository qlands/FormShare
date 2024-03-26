"""Upgrade FormShareDB to utf8mb4

Revision ID: 6fd9ba381bc6
Revises: 678c8daba0a3
Create Date: 2021-07-29 13:27:57.656173

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "6fd9ba381bc6"
down_revision = "678c8daba0a3"
branch_labels = None
depends_on = None


def upgrade():
    conn = op.get_bind()
    sql = (
        "ALTER DATABASE formshare CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci"
    )
    conn.execute(sql)
    sql = (
        "SELECT table_name FROM INFORMATION_SCHEMA.TABLES "
        "WHERE TABLE_TYPE = 'BASE TABLE' and TABLE_SCHEMA = 'formshare'"
    )
    res = conn.execute(sql)
    conn.execute("SET foreign_key_checks = 0")
    for a_record in res:
        sql = (
            "ALTER TABLE formshare.{} CONVERT TO CHARACTER "
            "SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(a_record[0])
        )
        conn.execute(sql)
    conn.execute("SET foreign_key_checks = 1")


def downgrade():
    pass
