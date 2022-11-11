"""Ugrade all dbs to utf8mb4

Revision ID: 678c8daba0a3
Revises: 3dd1ebdcd7e0
Create Date: 2021-07-13 10:12:39.296734

"""
from alembic import op
from formshare.models.formshare import Odkform
from sqlalchemy.orm.session import Session

# revision identifiers, used by Alembic.
revision = "678c8daba0a3"
down_revision = "3dd1ebdcd7e0"
branch_labels = None
depends_on = None


def upgrade():
    session = Session(bind=op.get_bind())
    forms = (
        session.query(Odkform.form_schema).filter(Odkform.form_schema.isnot(None)).all()
    )
    conn = op.get_bind()
    for a_form in forms:
        sql = "ALTER DATABASE {} CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci".format(
            a_form.form_schema
        )
        conn.execute(sql)
        sql = (
            "SELECT table_name FROM INFORMATION_SCHEMA.TABLES "
            "WHERE TABLE_TYPE = 'BASE TABLE' and TABLE_SCHEMA = '{}'".format(
                a_form.form_schema
            )
        )
        res = conn.execute(sql)
        conn.execute("SET foreign_key_checks = 0")
        for a_record in res:
            sql = (
                "ALTER TABLE {}.{} CONVERT TO CHARACTER "
                "SET utf8mb4 COLLATE utf8mb4_unicode_ci".format(
                    a_form.form_schema, a_record[0]
                )
            )
            conn.execute(sql)
        conn.execute("SET foreign_key_checks = 1")
    session.commit()


def downgrade():
    # No downgrade posible
    pass
