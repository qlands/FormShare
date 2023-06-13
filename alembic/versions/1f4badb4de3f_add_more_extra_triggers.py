"""Add more extra triggers

Revision ID: 1f4badb4de3f
Revises: d1ef48099a64
Create Date: 2023-06-13 10:19:00.704721

"""
from alembic import op
from sqlalchemy.orm.session import Session


# revision identifiers, used by Alembic.
revision = "1f4badb4de3f"
down_revision = "d1ef48099a64"
branch_labels = None
depends_on = None


def upgrade():
    session = Session(bind=op.get_bind())
    conn = op.get_bind()
    try:
        conn.execute(
            "CREATE TRIGGER partner_update_extra BEFORE UPDATE ON partner "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )
        conn.execute(
            "CREATE TRIGGER partnerproject_update_extra BEFORE UPDATE ON partnerproject "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )
        conn.execute(
            "CREATE TRIGGER partnerform_update_extra BEFORE UPDATE ON partnerform "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )
        conn.execute(
            "CREATE TRIGGER dictfield_update_extra BEFORE UPDATE ON dictfield "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )
        conn.execute(
            "CREATE TRIGGER dicttable_update_extra BEFORE UPDATE ON dicttable "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )

    except Exception as e:
        print(str(e))
        exit(1)

    session.commit()


def downgrade():
    session = Session(bind=op.get_bind())
    conn = op.get_bind()
    try:
        conn.execute("DROP TRIGGER partner_update_extra")
        conn.execute("DROP TRIGGER partnerproject_update_extra")
        conn.execute("DROP TRIGGER partnerform_update_extra")
        conn.execute("DROP TRIGGER dicttable_update_extra")
        conn.execute("DROP TRIGGER dictfield_update_extra")
    except Exception as e:
        print(str(e))
        exit(1)
    session.commit()
