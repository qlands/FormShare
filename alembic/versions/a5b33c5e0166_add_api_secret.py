"""Add API Secret

Revision ID: a5b33c5e0166
Revises: 7b448dc9906c
Create Date: 2022-05-13 07:05:09.227446

"""

import secrets

import sqlalchemy as sa
from alembic import op
from formshare.models.formshare import User, Collaborator
from sqlalchemy.orm.session import Session

# revision identifiers, used by Alembic.
revision = "a5b33c5e0166"
down_revision = "7b448dc9906c"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "collaborator",
        sa.Column("coll_apisecret", sa.Unicode(length=64), nullable=True),
    )
    op.add_column(
        "fsuser", sa.Column("user_apisecret", sa.Unicode(length=64), nullable=True)
    )
    session = Session(bind=op.get_bind())

    users = session.query(User.user_id, User.user_apisecret).all()
    for user in users:
        session.query(User).filter(User.user_id == user.user_id).update(
            {"user_apisecret": secrets.token_hex(16)}
        )

    collaborators = session.query(
        Collaborator.project_id, Collaborator.coll_id, Collaborator.coll_apisecret
    ).all()
    for collaborator in collaborators:
        session.query(Collaborator).filter(
            Collaborator.project_id == collaborator.project_id
        ).filter(Collaborator.coll_id == collaborator.coll_id).update(
            {"coll_apisecret": secrets.token_hex(16)}
        )
    session.commit()


def downgrade():
    op.drop_column("fsuser", "user_apisecret")
    op.drop_column("collaborator", "coll_apisecret")
