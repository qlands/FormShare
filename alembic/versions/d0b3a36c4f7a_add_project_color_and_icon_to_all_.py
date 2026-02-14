"""Add project color and icon to all projects

Revision ID: d0b3a36c4f7a
Revises: d5b5f9171d34
Create Date: 2021-07-29 15:27:36.822801

"""

import random

from alembic import op
from formshare.models.formshare import Project
from formshare.processes.color_hash import ColorHash
from sqlalchemy.orm.session import Session

# revision identifiers, used by Alembic.
revision = "d0b3a36c4f7a"
down_revision = "d5b5f9171d34"
branch_labels = None
depends_on = None


def upgrade():
    session = Session(bind=op.get_bind())
    projects = session.query(
        Project.project_id, Project.project_name, Project.project_code
    ).all()
    for a_project in projects:
        project_data = {
            "project_hexcolor": ColorHash(a_project.project_name).hex,
            "project_icon": "⭐",
        }
        session.query(Project).filter(
            Project.project_id == a_project.project_id
        ).update(project_data)
    session.commit()


def downgrade():
    pass
