"""Add ODK QR settings

Revision ID: 1903afedb92d
Revises: 75ded009ddaa
Create Date: 2023-09-05 09:29:07.013894

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1903afedb92d"
down_revision = "75ded009ddaa"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "project",
        sa.Column(
            "odk_update_mode",
            sa.INTEGER(),
            server_default=sa.text("'1'"),
            nullable=True,
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "odk_update_period",
            sa.INTEGER(),
            server_default=sa.text("'1'"),
            nullable=True,
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "odk_update_auto",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "odk_hide_old", sa.INTEGER(), server_default=sa.text("'1'"), nullable=True
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "odk_auto_send", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "odk_delete_after_send",
            sa.INTEGER(),
            server_default=sa.text("'0'"),
            nullable=True,
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "odk_high_res_video",
            sa.INTEGER(),
            server_default=sa.text("'1'"),
            nullable=True,
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "odk_image_size", sa.INTEGER(), server_default=sa.text("'1'"), nullable=True
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "odk_audio_app", sa.INTEGER(), server_default=sa.text("'0'"), nullable=True
        ),
    )
    op.add_column(
        "project",
        sa.Column(
            "odk_navigation", sa.INTEGER(), server_default=sa.text("'2'"), nullable=True
        ),
    )


def downgrade():
    op.drop_column("project", "odk_navigation")
    op.drop_column("project", "odk_audio_app")
    op.drop_column("project", "odk_image_size")
    op.drop_column("project", "odk_high_res_video")
    op.drop_column("project", "odk_delete_after_send")
    op.drop_column("project", "odk_auto_send")
    op.drop_column("project", "odk_hide_old")
    op.drop_column("project", "odk_update_auto")
    op.drop_column("project", "odk_update_period")
    op.drop_column("project", "odk_update_mode")
