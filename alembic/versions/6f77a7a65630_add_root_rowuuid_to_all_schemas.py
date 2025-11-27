"""Add root_rowuuid to all schemas

Revision ID: 6f77a7a65630
Revises: 0bc56c77ec06
Create Date: 2025-11-10 10:46:17.301860

"""

from alembic import op
from formshare.models.formshare import Odkform
from sqlalchemy.orm.session import Session
from sqlalchemy.exc import IntegrityError


# revision identifiers, used by Alembic.
revision = "6f77a7a65630"
down_revision = "0bc56c77ec06"
branch_labels = None
depends_on = None


def upgrade():
    session = Session(bind=op.get_bind())
    conn = op.get_bind()
    forms = (
        session.query(Odkform.form_schema).filter(Odkform.form_schema.isnot(None)).all()
    )
    for a_form in forms:
        try:
            sql = "SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA = '{}'".format(
                a_form.form_schema
            )
            tables = conn.execute(sql).fetchall()
            for a_table in tables:
                table_name = a_table[0]
                if not table_name.startswith("lkp") and not table_name.startswith(
                    "audit"
                ):
                    sql = (
                        "ALTER TABLE {}.{} ADD COLUMN root_rowuuid varchar(80)".format(
                            a_form.form_schema, table_name
                        )
                    )
                    conn.execute(sql)
        except Exception as e:
            if str(e).index("Duplicate column name") >= 0:
                pass
            else:
                raise e
    session.commit()


def downgrade():
    pass
