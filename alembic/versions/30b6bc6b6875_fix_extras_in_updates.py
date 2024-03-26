"""Fix extras in updates

Revision ID: 30b6bc6b6875
Revises: b1d4ed9b7aac
Create Date: 2020-07-26 12:57:30.195647

"""

from alembic import op
from sqlalchemy.orm.session import Session


# revision identifiers, used by Alembic.
revision = "30b6bc6b6875"
down_revision = "b1d4ed9b7aac"
branch_labels = None
depends_on = None


def upgrade():
    session = Session(bind=op.get_bind())
    conn = op.get_bind()
    try:
        conn.execute(
            "CREATE TRIGGER fsuser_update_extra BEFORE UPDATE ON fsuser "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )

        conn.execute(
            "CREATE TRIGGER project_update_extra BEFORE UPDATE ON project "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )

        conn.execute(
            "CREATE TRIGGER collaborator_update_extra BEFORE UPDATE ON collaborator "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )

        conn.execute(
            "CREATE TRIGGER collgroup_update_extra BEFORE UPDATE ON collgroup "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )

        conn.execute(
            "CREATE TRIGGER odkform_update_extra BEFORE UPDATE ON odkform "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )

        conn.execute(
            "CREATE TRIGGER formaccess_update_extra BEFORE UPDATE ON formaccess "
            "FOR EACH ROW BEGIN IF IFnull(OLD.extras,'{}') <> IFNULL(NEW.extras,'{}') THEN "
            "IF ISNULL(NEW.extras) = 0 THEN SET "
            "NEW.extras = JSON_MERGE_PATCH(IFnull(OLD.extras,'{}'),IFNULL(NEW.extras,'{}')); "
            "END IF; END IF; END;"
        )

        conn.execute(
            "CREATE TRIGGER formgrpaccess_update_extra BEFORE UPDATE ON formgrpaccess "
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
        conn.execute("DROP TRIGGER fsuser_update_extra")
        conn.execute("DROP TRIGGER project_update_extra")
        conn.execute("DROP TRIGGER collaborator_update_extra")
        conn.execute("DROP TRIGGER collgroup_update_extra")
        conn.execute("DROP TRIGGER odkform_update_extra")
        conn.execute("DROP TRIGGER formaccess_update_extra")
        conn.execute("DROP TRIGGER formgrpaccess_update_extra")
    except Exception as e:
        print(str(e))
        exit(1)
    session.commit()
