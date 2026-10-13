# coding: utf-8
import json

import sqlalchemy.types as types
from formshare.models.meta import Base
from sqlalchemy import (
    Column,
    DateTime,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    UniqueConstraint,
    INTEGER,
    BigInteger,
    Index,
    text,
    Unicode,
    DECIMAL,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT, BIGINT, DATETIME
from sqlalchemy.ext import mutable
from sqlalchemy.orm import relationship

metadata = Base.metadata


class JsonEncodedDict(types.TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""

    impl = MEDIUMTEXT(collation="utf8mb4_unicode_ci")

    def process_bind_param(self, value, dialect):
        if value is None:
            return "{}"
        else:
            return json.dumps(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return {}
        else:
            return json.loads(value)


mutable.MutableDict.associate_with(JsonEncodedDict)


class Collaboratorlog(Base):
    __tablename__ = "collaboratorlog"

    log_entry = Column(Unicode(64), primary_key=True)
    log_datetime = Column(DateTime)
    access_type = Column(INTEGER)
    interface = Column(INTEGER)
    action = Column(INTEGER)
    userid = Column(Unicode(255))
    org = Column(Unicode(32))
    project = Column(Unicode(32))
    form = Column(Unicode(120))
    collaborator = Column(Unicode(32))
    logid = Column(Unicode(64))
    commitid = Column(Unicode(12))
    schemaid = Column(Unicode(13))
    tableid = Column(Unicode(120))


class Tenant(Base):
    __tablename__ = "tenant"

    tenant_id = Column(Unicode(120), primary_key=True)
    tenant_name = Column(Unicode(120))
    tenant_cdate = Column(DateTime)
    tenant_active = Column(INTEGER, server_default=text("'0'"))
    tenant_main = Column(INTEGER, server_default=text("'0'"))
    fa_query_user = Column(Unicode(64))
    fa_query_password = Column(Unicode(256))
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))


class Roles(Base):
    __tablename__ = "role"

    role_id = Column(Unicode(64), primary_key=True)
    role_name = Column(Unicode(120))


class User(Base):
    __tablename__ = "fsuser"

    user_id = Column(Unicode(120), primary_key=True)
    user_name = Column(Unicode(120))
    user_email = Column(Unicode(120))
    user_password = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    user_assistant_password = Column(
        MEDIUMTEXT(collation="utf8mb4_unicode_ci")
    )  # For ODK Collect and Enketo
    user_about = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    user_cdate = Column(DateTime)
    user_llogin = Column(DateTime)
    user_super = Column(INTEGER, server_default=text("'0'"))
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    user_active = Column(INTEGER, server_default=text("'1'"))
    user_apikey = Column(Unicode(64))
    user_apisecret = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    user_apitoken = Column(Unicode(64))
    user_apitoken_expires_on = Column(DateTime)
    user_query_user = Column(Unicode(64))
    user_query_password = Column(Unicode(256))

    user_is_workspace = Column(INTEGER, server_default=text("'0'"))
    user_password_reset_key = Column(Unicode(64))
    user_password_reset_token = Column(Unicode(64))
    user_password_reset_expires_on = Column(DateTime)
    user_max_projects = Column(INTEGER, server_default=text("'1'"))
    user_max_submissions = Column(INTEGER, server_default=text("'500'"))
    user_kb_used = Column(DECIMAL(14, 3), server_default=text("'0'"))
    user_in_files_kb_used = Column(DECIMAL(14, 3), server_default=text("'0'"))
    user_in_files_last_event = Column(DateTime)
    user_in_files_last_read = Column(DateTime)

    user_timezone = Column(
        ForeignKey("timezone.timezone_code", ondelete="RESTRICT"),
        nullable=False,
        server_default=text("'UTC'"),
    )
    user_tenant = Column(
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"), nullable=False
    )

    timezone = relationship("TimeZone")
    tenant = relationship("Tenant")


class UserRoles(Base):
    __tablename__ = "userrole"

    user_id = Column(
        ForeignKey("fsuser.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    role_id = Column(
        ForeignKey("role.role_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    grant_date = Column(DateTime)

    role = relationship("Roles")
    user = relationship("User")


class Project(Base):
    __tablename__ = "project"

    project_id = Column(Unicode(64), primary_key=True)
    project_code = Column(Unicode(45))
    project_name = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    project_abstract = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    project_cdate = Column(DateTime)
    project_public = Column(INTEGER)
    project_archived = Column(INTEGER, server_default=text("'0'"))
    project_archiving = Column(INTEGER, server_default=text("'0'"))
    project_archived_by = Column(Unicode(120))
    project_archived_date = Column(DateTime)
    project_restoring = Column(INTEGER, server_default=text("'0'"))
    project_unarchived_by = Column(Unicode(120))
    project_unarchived_date = Column(DateTime)
    project_image = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    project_case = Column(INTEGER, server_default=text("'0'"))
    project_entities = Column(INTEGER, server_default=text("'0'"))
    project_encrypted = Column(INTEGER, server_default=text("'0'"))
    project_icon = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    project_formlist_auth = Column(INTEGER, server_default=text("'1'"))
    project_hexcolor = Column(Unicode(60))
    project_blob_storage = Column(INTEGER, server_default=text("'0'"))
    project_timezone = Column(
        ForeignKey("timezone.timezone_code", ondelete="RESTRICT"),
        nullable=False,
        server_default=text("'UTC'"),
    )
    project_tenant = Column(
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"), nullable=False
    )
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    # ODK Collect settings
    odk_update_mode = Column(
        INTEGER, server_default=text("'3'")
    )  # 1=manual, 2=previously_downloaded, 3=match_exactly
    odk_update_period = Column(
        INTEGER, server_default=text("'2'")
    )  # 1=every_fifteen_minutes, 2=every_one_hour, 3=every_six_hours, 4=every_24_hours
    odk_update_auto = Column(INTEGER, server_default=text("'1'"))
    odk_hide_old = Column(INTEGER, server_default=text("'1'"))

    odk_auto_send = Column(
        INTEGER, server_default=text("'0'")
    )  # 0=off, 1=wifi_only, 2=cellular_only, 3=wifi_and_cellular
    odk_delete_after_send = Column(INTEGER, server_default=text("'0'"))

    odk_high_res_video = Column(INTEGER, server_default=text("'1'"))
    odk_image_size = Column(
        INTEGER, server_default=text("'1'")
    )  # 1=original, 2=small, 3=very_small, 4=medium, 5=large
    odk_audio_app = Column(INTEGER, server_default=text("'0'"))
    odk_navigation = Column(
        INTEGER, server_default=text("'2'")
    )  # 1=swipe, 2=buttons, 3=swipe_buttons

    timezone = relationship("TimeZone")
    tenant = relationship("Tenant")


class Settings(Base):
    __tablename__ = "settings"

    settings_key = Column(Unicode(64), primary_key=True)
    settings_value = Column(JsonEncodedDict)


class Userlog(Base):
    __tablename__ = "userlog"

    log_entry = Column(Unicode(64), primary_key=True)
    log_datetime = Column(DateTime)
    access_type = Column(INTEGER)
    tableid = Column(Unicode(45))
    action = Column(INTEGER)
    userid = Column(Unicode(255))
    org = Column(Unicode(32))
    project = Column(Unicode(32))
    form = Column(Unicode(120))
    collaborator = Column(Unicode(32))
    groupid = Column(Unicode(12))
    septable = Column(Unicode(120))
    sepsection = Column(Unicode(12))
    sepitem = Column(Unicode(120))


class Collaborator(Base):
    __tablename__ = "collaborator"

    __table_args__ = (
        Index("unique_project_coll_id", "project_id", "coll_id", unique=True),
    )

    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=False,
        nullable=True,
    )
    coll_uuid = Column(Unicode(120), primary_key=True, nullable=False)
    coll_type = Column(
        INTEGER, server_default=text("'1'")
    )  # 1 = Project assistant, 2=A collaborator
    coll_id = Column(Unicode(120), primary_key=False, nullable=True)
    coll_name = Column(Unicode(120))
    coll_password = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    coll_active = Column(INTEGER)
    coll_cdate = Column(DateTime)
    coll_email = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    coll_telephone = Column(Unicode(120))
    coll_prjshare = Column(INTEGER)
    coll_apikey = Column(Unicode(64))
    coll_apisecret = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    coll_apitoken = Column(Unicode(64))
    coll_apitoken_expires_on = Column(DateTime)
    coll_query_user = Column(Unicode(64))
    coll_query_password = Column(Unicode(256))
    coll_timezone = Column(
        ForeignKey("timezone.timezone_code", ondelete="RESTRICT"),
        nullable=False,
        server_default=text("'UTC'"),
    )
    coll_tenant = Column(
        ForeignKey("tenant.tenant_id", ondelete="RESTRICT"), nullable=True
    )
    linked_user = Column(ForeignKey("fsuser.user_id", ondelete="CASCADE"), index=True)

    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    project = relationship("Project")
    timezone = relationship("TimeZone")
    tenant = relationship("Tenant")
    fsuser = relationship("User")


class Partner(Base):
    __tablename__ = "partner"

    partner_id = Column(Unicode(64), primary_key=True, nullable=False)
    partner_email = Column(Unicode(320), nullable=False)
    partner_name = Column(Unicode(120))
    partner_organization = Column(Unicode(120))
    partner_password = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    partner_cdate = Column(DateTime)
    partner_telephone = Column(Unicode(120))
    partner_apikey = Column(Unicode(64))
    partner_apisecret = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    partner_query_user = Column(Unicode(64))
    partner_query_password = Column(Unicode(256))
    created_by = Column(
        ForeignKey("fsuser.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    partner_timezone = Column(
        ForeignKey("timezone.timezone_code", ondelete="RESTRICT"),
        nullable=False,
        server_default=text("'UTC'"),
    )
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    fsuser = relationship("User")
    timezone = relationship("TimeZone")


class PartnerProject(Base):
    __tablename__ = "partnerproject"

    partner_id = Column(
        ForeignKey("partner.partner_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    access_date = Column(DateTime)
    granted_by = Column(
        ForeignKey("fsuser.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    time_bound = Column(INTEGER, server_default=text("'0'"))
    access_from = Column(Date)
    access_to = Column(Date)
    query_access = Column(INTEGER, server_default=text("'0'"))
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    project = relationship("Project")
    partner = relationship("Partner")
    fsuser = relationship("User")


class PartnerForm(Base):
    __tablename__ = "partnerform"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
        Index("fk_partnerform_form1_idx", "project_id", "form_id"),
    )
    partner_id = Column(
        ForeignKey("partner.partner_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    access_date = Column(DateTime)
    granted_by = Column(
        ForeignKey("fsuser.user_id", ondelete="CASCADE"),
        nullable=False,
    )
    time_bound = Column(INTEGER, server_default=text("'0'"))
    access_from = Column(Date)
    access_to = Column(Date)
    query_access = Column(INTEGER, server_default=text("'0'"))
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    odkform = relationship("Odkform")
    partner = relationship("Partner")
    fsuser = relationship("User")


class ProjectFile(Base):
    __tablename__ = "projectfile"

    file_id = Column(Unicode(64), primary_key=True, nullable=False)
    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"), nullable=False
    )
    file_name = Column(Unicode(120))
    file_udate = Column(DateTime)

    project = relationship("Project")


class Collgroup(Base):
    __tablename__ = "collgroup"

    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    group_id = Column(Unicode(12), primary_key=True, nullable=False)
    group_desc = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    group_cdate = Column(DateTime)
    group_active = Column(INTEGER)
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    project = relationship("Project")


class ProjectSettings(Base):
    __tablename__ = "prjsettings"

    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    settings_key = Column(Unicode(64), primary_key=True)
    settings_value = Column(JsonEncodedDict)

    project = relationship("Project")


class FinishedTask(Base):
    __tablename__ = "finishedtask"
    task_id = Column(Unicode(64), primary_key=True, nullable=False)
    task_enumber = Column(INTEGER)
    task_error = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))


class TimeZone(Base):
    __tablename__ = "timezone"
    timezone_code = Column(Unicode(64), primary_key=True, nullable=False)
    timezone_name = Column(Unicode(64))
    timezone_utc_offset = Column(Unicode(6))
    timezone_utc_dst_offset = Column(Unicode(6))


class Odkform(Base):
    __tablename__ = "odkform"
    __table_args__ = (
        ForeignKeyConstraint(
            ["parent_project", "parent_form"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
        Index("fk_form_form1_idx", "parent_project", "parent_form"),
    )

    project_id = Column(
        ForeignKey("project.project_id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    form_name = Column(Unicode(120))
    form_cdate = Column(DateTime)
    form_lupdate = Column(DateTime)
    form_pubby = Column(
        ForeignKey("fsuser.user_id", ondelete="CASCADE"), nullable=False
    )
    form_directory = Column(Unicode(120))
    form_target = Column(INTEGER)
    form_schema = Column(Unicode(64))
    form_accsub = Column(INTEGER)
    form_blocked = Column(INTEGER, server_default=text("'0'"))
    form_testing = Column(INTEGER, server_default=text("'0'"))
    form_incversion = Column(INTEGER, server_default=text("'0'"))
    parent_project = Column(Unicode(64))
    parent_form = Column(Unicode(120))
    form_stage = Column(INTEGER)
    form_pkey = Column(Unicode(120))
    form_deflang = Column(Unicode(120))
    form_othlangs = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_mergetask = Column(Unicode(64))
    form_abletomerge = Column(INTEGER, server_default=text("'-1'"))
    form_mergelngerror = Column(INTEGER, server_default=text("'0'"))
    form_repositorypossible = Column(INTEGER, server_default=text("'-1'"))
    form_mergerrors = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_xlsfile = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_xmlfile = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_jsonfile = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_createxmlfile = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_insertxmlfile = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_reqfiles = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_surveycolumns = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_choicescolumns = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_invalidcolumns = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_public = Column(INTEGER)
    form_geopoint = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    # The geotraces and geoshapes of the main table, in form order, as
    # "group/name:type" -- what the map draws (processes/geometry.py).
    form_geoshape = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_hexcolor = Column(Unicode(60))
    form_reptask = Column(Unicode(64))
    form_version = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_index = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_type = Column(INTEGER, server_default=text("'1'"))
    # Actions (feature 3, decision 16): how the form's module is written --
    # "table", compiled from its PropertyAction rows, or "expert", written by
    # the owner -- and the module itself, compiled or written, which is what
    # the server runs after each load and what actions.json serves. NULL or
    # empty: no actions. docs/formshare_case_management/actions-api.md.
    action_mode = Column(Unicode(10), server_default=text("'table'"))
    action_module = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_case = Column(INTEGER, server_default=text("'0'"))
    form_casetype = Column(
        INTEGER, server_default=text("'0'")
    )  # 1=Creator, 2= Follow up, 3= Deactivate, 4= Activate
    form_caselabel = Column(Unicode(120))
    form_caseselector = Column(Unicode(120))
    form_casedatetime = Column(Unicode(120))
    form_caseselectorfilename = Column(Unicode(120))
    form_caseselectorlastgen = Column(DateTime)
    form_hasdictionary = Column(INTEGER, server_default=text("'0'"))
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    parent = relationship("Odkform", remote_side=[project_id, form_id])
    project = relationship("Project")
    fsuser = relationship("User")


class MediaFile(Base):
    __tablename__ = "mediafile"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
    )

    file_id = Column(Unicode(64), primary_key=True, nullable=False)
    project_id = Column(Unicode(64), nullable=False)
    form_id = Column(Unicode(120), nullable=False)
    file_name = Column(Unicode(120))
    file_udate = Column(DateTime)
    file_md5 = Column(Unicode(64))
    file_mimetype = Column(Unicode(120))
    file_realtimecsv = Column(INTEGER, server_default=text("'0'"))
    file_lastgen = Column(DateTime)

    project = relationship("Odkform")


class Product(Base):
    __tablename__ = "product"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
    )

    celery_taskid = Column(Unicode(64), primary_key=True, nullable=False)
    output_file = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    output_size = Column(BIGINT(unsigned=True), server_default=text("'0'"))
    project_id = Column(Unicode(64), nullable=False)
    form_id = Column(Unicode(120), nullable=False)
    product_id = Column(Unicode(120), nullable=False)
    output_id = Column(Unicode(64), nullable=False)
    output_mimetype = Column(Unicode(120))
    process_only = Column(INTEGER, server_default=text("'0'"))
    report_updates = Column(INTEGER, server_default=text("'1'"))
    product_desc = Column(Unicode(120))
    datetime_added = Column(DateTime)
    product_published = Column(INTEGER, server_default=text("'0'"))
    published_by = Column(ForeignKey("fsuser.user_id", ondelete="CASCADE"), index=True)
    date_published = Column(DateTime)
    last_download = Column(DateTime)
    downloads = Column(INTEGER, server_default=text("'0'"))
    created_by = Column(
        ForeignKey("fsuser.user_id", ondelete="CASCADE"), nullable=False, index=True
    )
    publishable = Column(INTEGER, server_default=text("'0'"))

    odkform = relationship("Odkform")
    fsuser = relationship("User", primaryjoin="Product.created_by == User.user_id")
    fsuser1 = relationship("User", primaryjoin="Product.published_by == User.user_id")


class Userproject(Base):
    __tablename__ = "userproject"

    user_id = Column(
        ForeignKey("fsuser.user_id", ondelete="RESTRICT"),
        primary_key=True,
        nullable=False,
    )
    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    access_type = Column(INTEGER)  # 1=Owner,2=Admin,3=Editor,4=Member.
    access_date = Column(DateTime)
    project_active = Column(INTEGER, server_default=text("'1'"))
    project_accepted = Column(INTEGER, server_default=text("'1'"))
    project_accepted_date = Column(DateTime)

    project = relationship("Project")
    user = relationship("User")


class Collingroup(Base):
    __tablename__ = "collingroup"
    __table_args__ = (
        ForeignKeyConstraint(
            ["coll_uuid"],
            ["collaborator.coll_uuid"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["project_id", "group_id"],
            ["collgroup.project_id", "collgroup.group_id"],
            ondelete="CASCADE",
        ),
        Index("fk_enumingroup_collaborator_idx", "coll_uuid"),
        Index("fk_enumingroup_group_idx", "project_id", "group_id"),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    group_id = Column(Unicode(12), primary_key=True, nullable=False)
    enum_project = Column(Unicode(64), primary_key=False, nullable=True)
    coll_id = Column(Unicode(120), primary_key=False, nullable=True)
    coll_uuid = Column(Unicode(120), primary_key=True, nullable=False)
    join_date = Column(DateTime)

    collaborator = relationship("Collaborator")
    project = relationship("Collgroup")


class Formacces(Base):
    __tablename__ = "formaccess"
    __table_args__ = (
        ForeignKeyConstraint(
            ["form_project", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["coll_uuid"],
            ["collaborator.coll_uuid"],
            ondelete="CASCADE",
        ),
        Index("fk_submitter_project", "form_project", "form_id"),
        Index("fk_submitter_collaborator", "coll_uuid"),
    )

    coll_uuid = Column(Unicode(120), primary_key=True, nullable=False)
    form_project = Column(Unicode(64), primary_key=True, nullable=False)
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    coll_can_submit = Column(INTEGER, server_default=text("'0'"))
    coll_can_clean = Column(INTEGER, server_default=text("'0'"))
    coll_can_query = Column(INTEGER, server_default=text("'0'"))
    coll_is_supervisor = Column(INTEGER, server_default=text("'0'"))
    access_date = Column(DateTime)
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    odkform = relationship("Odkform")
    project = relationship("Collaborator")


class Formgrpacces(Base):
    __tablename__ = "formgrpaccess"
    __table_args__ = (
        ForeignKeyConstraint(
            ["form_project", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["project_id", "group_id"],
            ["collgroup.project_id", "collgroup.group_id"],
            ondelete="CASCADE",
        ),
        Index("fk_grpsubmitter_form1_idx", "form_project", "form_id"),
        Index("fk_grpsubmitter_form1", "form_project", "form_id"),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    group_id = Column(Unicode(12), primary_key=True, nullable=False)
    form_project = Column(Unicode(64), primary_key=True, nullable=False)
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    group_can_submit = Column(INTEGER, server_default=text("'0'"))
    group_can_clean = Column(INTEGER, server_default=text("'0'"))
    group_is_supervisor = Column(INTEGER, server_default=text("'0'"))
    access_date = Column(DateTime)
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    odkform = relationship("Odkform")
    project = relationship("Collgroup")


class Jsonlog(Base):
    __tablename__ = "jsonlog"
    __table_args__ = (
        ForeignKeyConstraint(
            ["coll_uuid"],
            ["collaborator.coll_uuid"],
        ),
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
        Index("fk_jsonlog_form1_idx", "project_id", "form_id"),
        Index("fk_jsonlog_enumerator1_idx", "coll_uuid"),
    )

    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    log_id = Column(Unicode(64), primary_key=True, nullable=False)
    log_dtime = Column(DateTime)
    json_file = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    log_file = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    command_executed = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    status = Column(INTEGER)
    coll_uuid = Column(Unicode(120))

    collaborator = relationship("Collaborator")
    project = relationship("Odkform")


class Submission(Base):
    __tablename__ = "submission"
    __table_args__ = (
        ForeignKeyConstraint(
            ["coll_uuid"],
            ["collaborator.coll_uuid"],
        ),
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
        Index("fk_submission_enumerator1_idx", "coll_uuid"),
        Index("fk_submission_form1_idx", "project_id", "form_id"),
        Index(
            "idx_submission_fast",
            "project_id",
            "form_id",
            "original_md5sum",
            "sameas",
            "submission_id",
        ),
        Index(
            "idx_submission_last", "project_id", "form_id", "sameas", "submission_dtime"
        ),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    submission_id = Column(Unicode(64), primary_key=True, nullable=False)
    submission_dtime = Column(DateTime)
    submission_status = Column(INTEGER)
    coll_uuid = Column(Unicode(120))
    md5sum = Column(Unicode(120))
    original_md5sum = Column(Unicode(120))
    sameas = Column(Unicode(64))
    submission_size = Column(BIGINT(unsigned=True), server_default=text("'0'"))

    collaborator = relationship("Collaborator")
    project = relationship("Odkform")


class FormSettings(Base):
    __tablename__ = "formsettings"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
        Index("fk_settings_form1_idx", "project_id", "form_id"),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    settings_key = Column(Unicode(64), primary_key=True)
    settings_value = Column(JsonEncodedDict)

    project = relationship("Odkform")


class Jsonhistory(Base):
    __tablename__ = "jsonhistory"
    __table_args__ = (
        ForeignKeyConstraint(
            ["coll_uuid"],
            ["collaborator.coll_uuid"],
        ),
        ForeignKeyConstraint(
            ["form_id", "project_id", "log_id"],
            ["jsonlog.form_id", "jsonlog.project_id", "jsonlog.log_id"],
            ondelete="CASCADE",
        ),
        Index("fk_jsonhistory_enumerator1_idx", "coll_uuid"),
        Index("fk_jsonhistory_jsonlog1_idx", "form_id", "project_id", "log_id"),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    log_id = Column(Unicode(64), primary_key=True, nullable=False)
    log_sequence = Column(Unicode(12), primary_key=True, nullable=False)
    log_dtime = Column(DateTime)
    log_action = Column(INTEGER)
    log_commit = Column(Unicode(12))
    log_notes = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    coll_uuid = Column(Unicode(120))

    collaborator = relationship("Collaborator")
    form = relationship("Jsonlog")


class DictTable(Base):
    __tablename__ = "dicttable"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["parent_project", "parent_form", "parent_table"],
            ["dicttable.project_id", "dicttable.form_id", "dicttable.table_name"],
            ondelete="CASCADE",
        ),
        Index(
            "fk_dicttable_dicttable_idx",
            "parent_project",
            "parent_form",
            "parent_table",
        ),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    table_name = Column(Unicode(120), primary_key=True, nullable=False)
    table_index = Column(
        BigInteger, index=True, autoincrement=True, unique=True, nullable=False
    )
    table_desc = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=False)
    table_lkp = Column(INTEGER, server_default=text("'0'"), nullable=False)
    table_inserttrigger = Column(Unicode(64))
    table_xmlcode = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    parent_project = Column(Unicode(64))
    parent_form = Column(Unicode(120))
    parent_table = Column(Unicode(120))
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    parent = relationship("DictTable", remote_side=[project_id, form_id, table_name])
    project = relationship("Odkform")


class DictField(Base):
    __tablename__ = "dictfield"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id", "table_name"],
            ["dicttable.project_id", "dicttable.form_id", "dicttable.table_name"],
            ondelete="CASCADE",
        ),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    table_name = Column(Unicode(120), primary_key=True, nullable=False)
    field_name = Column(Unicode(120), primary_key=True, nullable=False)
    field_index = Column(
        BigInteger, index=True, autoincrement=True, unique=True, nullable=False
    )
    field_desc = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    field_xmlcode = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    field_type = Column(Unicode(64))
    field_odktype = Column(Unicode(64))
    field_rtable = Column(Unicode(120))
    field_rfield = Column(Unicode(120))
    field_rlookup = Column(INTEGER, server_default=text("'0'"))
    field_key = Column(INTEGER, server_default=text("'0'"))
    field_rname = Column(Unicode(64))
    field_selecttype = Column(INTEGER, server_default=text("'0'"))
    field_externalfilename = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    field_codecolumn = Column(Unicode(120))
    field_desccolumn = Column(Unicode(120))
    field_size = Column(INTEGER, server_default=text("'0'"))
    field_decsize = Column(INTEGER, server_default=text("'0'"))
    field_sensitive = Column(INTEGER, server_default=text("'0'"))
    field_protection = Column(Unicode(64))
    field_encrypted = Column(INTEGER, server_default=text("'0'"))
    field_unique = Column(INTEGER, server_default=text("'0'"))
    field_ontology = Column(Unicode(120))
    # Schema format 3.0 attributes. They say what a lookup row is and what may
    # be written to a column, which is what a replaced CSV or GeoJSON needs to
    # know before it merges anything into a live lookup table.
    field_rfilter = Column(Unicode(1024))
    field_generatedas = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    field_autoincrement = Column(INTEGER, server_default=text("'0'"))
    field_notnull = Column(INTEGER, server_default=text("'0'"))
    field_srid = Column(Unicode(64))
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    dicttable = relationship("DictTable")


class CaseLookUp(Base):
    __tablename__ = "caselookup"

    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"), primary_key=True
    )
    field_name = Column(Unicode(120), primary_key=True)
    field_as = Column(Unicode(120))
    field_editable = Column(INTEGER, server_default=text("'1'"))

    project = relationship("Project")


class PublishedList(Base):
    """A real-time file the project publishes from a repository table.

    The registry of docs/formshare_case_management/ (formshare.md section 2.1).
    The key column of every list is rowuuid and is deliberately not a column
    here: making it configurable would invite the 2021 mistake back.
    """

    __tablename__ = "publishedlist"
    __table_args__ = (
        ForeignKeyConstraint(
            ["source_project", "source_form"],
            ["odkform.project_id", "odkform.form_id"],
        ),
        UniqueConstraint("project_id", "list_filename"),
    )

    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    list_id = Column(Unicode(120), primary_key=True, nullable=False)
    list_filename = Column(Unicode(120), nullable=False)
    list_format = Column(Unicode(12), nullable=False, server_default=text("'csv'"))
    source_project = Column(Unicode(64), nullable=False)
    source_form = Column(Unicode(120), nullable=False)
    source_table = Column(Unicode(120), nullable=False)
    label_column = Column(Unicode(120), nullable=False)
    # The list's filter as the owner built it, QueryBuilder's JSON, which is
    # the stored truth; filter_sql is compiled from it (processes/list_filter.py).
    filter_rules = Column(MEDIUMTEXT())
    filter_sql = Column(MEDIUMTEXT())
    geometry_column = Column(Unicode(120))
    list_filter_mode = Column(Unicode(20), server_default=text("'all'"))
    list_active = Column(INTEGER, server_default=text("'1'"))
    list_key_column = Column(Unicode(120))
    list_lastgen = Column(DateTime)
    list_seq = Column(INTEGER, server_default=text("'0'"))
    # A GeoJSON list's last generation left out this many cases -- no
    # location, or one that cannot be the geometry asked for -- which are on
    # no map until they have one. NULL for a CSV list.
    list_skipped = Column(INTEGER)
    list_createdate = Column(DateTime)

    project = relationship(
        "Project", primaryjoin="PublishedList.project_id == Project.project_id"
    )


class PublishedListColumn(Base):
    """Which source columns a published list serves, in order."""

    __tablename__ = "publishedlistcolumn"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "list_id"],
            ["publishedlist.project_id", "publishedlist.list_id"],
            ondelete="CASCADE",
        ),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    list_id = Column(Unicode(120), primary_key=True, nullable=False)
    column_name = Column(Unicode(120), primary_key=True, nullable=False)
    column_source = Column(Unicode(20), nullable=False, server_default=text("'table'"))
    column_as = Column(Unicode(120))
    column_order = Column(INTEGER, server_default=text("'0'"))

    publishedlist = relationship("PublishedList")


class ListConsumer(Base):
    """A form that feeds, reads or updates a published list.

    Written when a form upload matches an attachment name against the
    registry. consumer_is_link marks the one reference whose FK and trigger
    make the form a follow-up of that list's rows (the case link); the rest
    are auxiliary reads.
    """

    __tablename__ = "listconsumer"
    __table_args__ = (
        ForeignKeyConstraint(
            ["list_project", "list_id"],
            ["publishedlist.project_id", "publishedlist.list_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["consumer_project", "consumer_form"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
    )

    list_project = Column(Unicode(64), primary_key=True, nullable=False)
    list_id = Column(Unicode(120), primary_key=True, nullable=False)
    consumer_project = Column(Unicode(64), primary_key=True, nullable=False)
    consumer_form = Column(Unicode(120), primary_key=True, nullable=False)
    consumer_role = Column(Unicode(20), nullable=False, server_default=text("'reads'"))
    selector_field = Column(Unicode(120))
    consumer_is_link = Column(INTEGER, server_default=text("'0'"))

    publishedlist = relationship("PublishedList")
    odkform = relationship("Odkform")


class TableProperty(Base):
    """A property of a source table (feature 2).

    A typed column of <table>_properties, a table FormShare keeps beside the
    source table, 1:1 on rowuuid, outside the RSTools contract. A property is
    state the workflow writes -- a patient's risk factor set by each follow-up
    -- so it is defined by a type and a default, not copied from a variable:
    every row starts at the default (the creation trigger gives a new row its
    property row) and follow-up actions (feature 3) set it afterwards.
    docs/formshare_case_management/formshare.md sections 2.3, 3.1.
    """

    __tablename__ = "tableproperty"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    table_name = Column(Unicode(120), primary_key=True, nullable=False)
    property_name = Column(Unicode(120), primary_key=True, nullable=False)
    # string, integer, decimal, date, datetime, geopoint, geotrace, geoshape
    property_type = Column(Unicode(20), nullable=False)
    # The value every row starts with; NULL when empty. Validated against
    # the type at definition (validate_property_default).
    property_default = Column(Unicode(255))
    property_desc = Column(Unicode(500))
    property_cdate = Column(DateTime)

    odkform = relationship("Odkform")


class PropertyAction(Base):
    """A row of a form's decision table (feature 3, decision 16).

    "When this form is submitted, set X to Y if Z", one row per line. The
    rows are compiled, in action_order, into the form's JavaScript module
    (Odkform.action_module) by processes/actions/compiler.py; the module is
    what runs, on the server after each load and on the device at
    finalize. The closed grammar is the schema: there is no expression
    column here -- an expression lives in expert mode, as code. The
    condition is jQuery QueryBuilder's rule JSON, NULL for "always".
    docs/formshare_case_management/formshare.md section 2.5, actions-api.md.
    """

    __tablename__ = "propertyaction"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
    )

    action_id = Column(Unicode(64), primary_key=True, nullable=False)
    project_id = Column(Unicode(64), nullable=False)
    form_id = Column(Unicode(120), nullable=False)
    action_order = Column(INTEGER, nullable=False, server_default=text("'0'"))
    # case | parent: the linked case, or the row it belongs to
    target_scope = Column(Unicode(10), nullable=False, server_default=text("'case'"))
    # property | column | active
    target_kind = Column(Unicode(10), nullable=False)
    # the property or column name; "0" / "1" for active
    target_name = Column(Unicode(120))
    # constant | variable | now | computed
    value_kind = Column(Unicode(10), nullable=False)
    # the constant, the variable, or the computed spec as JSON
    # ({"aggregate", "repeat", "column", "filter"})
    value = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    # QueryBuilder rule JSON; NULL = always
    when_rules = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    action_cdate = Column(DateTime)

    odkform = relationship("Odkform")


class ActionRun(Base):
    """What the module did to one submission, or why it could not.

    One row per run on the server: the change report of actions-api.md
    section 9 when it succeeded, the failure message with its line when it
    did not. A failed run leaves the submission loaded and is retried from
    the logs page (formshare.md section 3.3).
    """

    __tablename__ = "actionrun"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
    )

    run_id = Column(Unicode(64), primary_key=True, nullable=False)
    project_id = Column(Unicode(64), nullable=False)
    form_id = Column(Unicode(120), nullable=False)
    submission_id = Column(Unicode(64))
    # The submission's meta/instanceID: how a device knows it, where
    # submission_id is the server's own name for it.
    instance_id = Column(Unicode(120))
    main_rowuuid = Column(Unicode(80), nullable=False)
    run_dtime = Column(DateTime)
    # 0 = applied, 1 = failed, 2 = taken back: the submission's rows were
    # deleted and what the run wrote to other rows was put back. A dry run
    # is never recorded.
    run_status = Column(INTEGER, nullable=False, server_default=text("'0'"))
    run_message = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    run_changes = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    # What each column the run changed held before it, as MySQL spells it
    # (CAST AS CHAR), read when the writes were planned, so that a take-back
    # puts it back exactly. run_changes is for people and spells a number as
    # JavaScript does: a decimal(17,3) with thirteen or fourteen digits before
    # the point does not survive that (rstools.md 24.1). Runs recorded
    # before it have none, and are taken back from run_changes.
    run_restore = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    run_log = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    odkform = relationship("Odkform")


# ---------------------------------------------------------------------------
# Field encryption (docs/formshare_field_encryption/, formshare.md section 2)
#
# The server keeps public keys, member keys locked in a browser, grants sealed
# in a browser, and the record of who did what. Nothing here opens anything:
# every binary value is the base64url text the formats define, kept as the
# browser sent it.
# ---------------------------------------------------------------------------


class EncryptionProjectKey(Base):
    """A version of a project's key: its public half.

    Answers to marked questions are sealed to the active version the moment
    they arrive. A rotation retires it, and the retired versions stay, to
    open the answers sealed to them. One active version per project, which
    a functional unique index on the table holds (the migration's).
    """

    __tablename__ = "encryption_project_key"

    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    # The first 8 bytes of SHA-256 of the key, in hex: the key's fingerprint.
    key_id = Column(Unicode(16), primary_key=True, nullable=False)
    # fsenc-pk:1:<key id>:<key>
    public_key = Column(Unicode(100), nullable=False)
    # active | retired
    key_status = Column(Unicode(10), nullable=False)
    created_by = Column(Unicode(120))
    created_date = Column(DATETIME(fsp=6))
    retired_date = Column(DATETIME(fsp=6))
    # The version's signing key, derived in a browser from its private key:
    # fsenc-spk:1:<key id>:<key>. Its signature vouches for the next version
    # and for every grant of this one (README 3.6), so that a write only a
    # holder of the key can make is told from one a stolen session makes.
    sign_public_key = Column(Unicode(100))
    # The version whose signing key signed this one's public key: the one it
    # replaced, or itself for the project's first. A vault follows these
    # from the first version to the active one.
    signed_by = Column(Unicode(16))
    # b64u of the Ed25519 signature of fsenc-kv:1:<signed_by>:<public key>.
    # The three are NULL only for a key set up before versions were signed.
    key_signature = Column(Unicode(100))

    project = relationship("Project")


class EncryptionMember(Base):
    """Someone who can hold a project's key: a user, an assistant, or a
    project's recovery kit, which is a member with no person behind it.

    Its key pair is made in its browser (or derived from the kit), and only
    the public half is here. One active member per user, per assistant and
    per project's kit, held by the migration's functional unique indexes; a
    replaced one keeps its row, revoked, for the record.
    """

    __tablename__ = "encryption_member"

    member_id = Column(Unicode(64), primary_key=True)
    # user | assistant | recovery
    member_type = Column(Unicode(10), nullable=False)
    user_id = Column(ForeignKey("fsuser.user_id", ondelete="CASCADE"), index=True)
    # An assistant is a collaborator row: coll_uuid is what formaccess and
    # the assistant's session know it by.
    coll_uuid = Column(
        ForeignKey("collaborator.coll_uuid", ondelete="CASCADE"), index=True
    )
    # The project of a recovery kit.
    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"), index=True
    )
    # fsenc-mk:1:<key>
    public_key = Column(Unicode(100), nullable=False)
    created_date = Column(DATETIME(fsp=6))
    revoked_date = Column(DATETIME(fsp=6))


class EncryptionUnlock(Base):
    """A member's private key, locked in its browser by one unlock method: a
    passkey's PRF output or a passphrase stretched with Argon2id. Each method
    is one more locked copy of the same key; a member keeps at least one."""

    __tablename__ = "encryption_unlock"

    unlock_id = Column(Unicode(64), primary_key=True)
    member_id = Column(
        ForeignKey("encryption_member.member_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # passkey | passphrase
    unlock_method = Column(Unicode(10), nullable=False)
    unlock_label = Column(Unicode(120))
    # A passkey's WebAuthn credential id, base64url.
    credential_id = Column(Unicode(1400))
    # JSON. A passkey: {prf_salt}; a passphrase: {salt, opslimit, memlimit,
    # alg}, kept so that they can be raised.
    unlock_params = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    # JSON {nonce, box}: crypto_secretbox_easy of the member's private key.
    locked_key = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=False)
    created_date = Column(DATETIME(fsp=6))
    last_used_date = Column(DATETIME(fsp=6))


class EncryptionGrant(Base):
    """A version of a project's private key, sealed in a browser to a
    member's public key and signed by that version's signing key, for that
    member: fsenc-grant:3:<key id>:<sealed key>:<signature>. One per member
    per version."""

    __tablename__ = "encryption_grant"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "key_id"],
            ["encryption_project_key.project_id", "encryption_project_key.key_id"],
            ondelete="CASCADE",
        ),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    key_id = Column(Unicode(16), primary_key=True, nullable=False)
    member_id = Column(
        ForeignKey("encryption_member.member_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    grant_value = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"), nullable=False)
    # The member whose browser made it: a person, or the recovery kit.
    granted_by = Column(Unicode(64))
    granted_date = Column(DATETIME(fsp=6))


class EncryptionEvent(Base):
    """The record of field encryption, append only. No foreign keys: the
    record outlives what it is about."""

    __tablename__ = "encryption_event"
    __table_args__ = (Index("ix_encryption_event_project", "project_id", "event_date"),)

    event_id = Column(Unicode(64), primary_key=True)
    # NULL for what concerns a member alone: an enrolment, an unlock method.
    project_id = Column(Unicode(64))
    # user | assistant | system
    actor_type = Column(Unicode(10), nullable=False)
    actor_id = Column(Unicode(120))
    # setup, enroll, unlock_method_added, unlock_method_removed, unlock,
    # grant, revoke, rotate, recovery_used, recovery_replaced, key_alarm,
    # decrypted
    event_type = Column(Unicode(30), nullable=False)
    event_detail = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    # To the microsecond: the record is read in the order things happened.
    event_date = Column(DATETIME(fsp=6), nullable=False)
    ip = Column(Unicode(45))
    user_agent = Column(Unicode(512))


class CookieConsent(Base):
    __tablename__ = "cookieconsent"

    consent_id = Column(Unicode(64), primary_key=True)
    consent_ip = Column(Unicode(45), index=True)
    consent_cdate = Column(DateTime)
    consent_udate = Column(DateTime)
    consent_essential = Column(INTEGER)
    consent_functional = Column(INTEGER)
    consent_analytical = Column(INTEGER)
    consent_marketing = Column(INTEGER)


class CookieConsentLog(Base):
    __tablename__ = "cookieconsentlog"

    log_id = Column(Unicode(64), primary_key=True)
    log_ip = Column(Unicode(45))
    log_date = Column(DateTime)
    log_action = Column(Unicode(20))
    log_essential = Column(INTEGER)
    log_functional = Column(INTEGER)
    log_analytical = Column(INTEGER)
    log_marketing = Column(INTEGER)
