"""Upgrade audit table

Revision ID: be94ab1faa43
Revises: a63e75eb09b1
Create Date: 2020-04-26 13:51:46.959097

"""
from alembic import op
from sqlalchemy.orm.session import Session
from formshare.models.formshare import Odkform


# revision identifiers, used by Alembic.
revision = 'be94ab1faa43'
down_revision = 'a63e75eb09b1'
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
            conn.execute(
                "alter table {}.audit_log modify column audit_id varchar(64)".format(
                    a_form.form_schema
                )
            )
            conn.execute(
                "alter table {}.audit_log modify column audit_date timestamp(6)".format(
                    a_form.form_schema
                )
            )
            conn.execute(
                "alter table {}.audit_log modify column audit_oldvalue text".format(
                    a_form.form_schema
                )
            )
            conn.execute(
                "alter table {}.audit_log modify column audit_newvalue text".format(
                    a_form.form_schema
                )
            )

        except Exception as e:
            print(str(e))

    session.commit()


def downgrade():
    print("No downgrade available")
