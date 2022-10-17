# coding: utf-8
import json

import sqlalchemy.types as types
from sqlalchemy import (
    Column,
    DateTime,
    Date,
    ForeignKey,
    ForeignKeyConstraint,
    INTEGER,
    BigInteger,
    Index,
    text,
    Unicode,
)
from sqlalchemy.dialects.mysql import MEDIUMTEXT
from sqlalchemy.ext import mutable
from sqlalchemy.orm import relationship

from formshare.models.meta import Base

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


class User(Base):
    __tablename__ = "fsuser"

    user_id = Column(Unicode(120), primary_key=True)
    user_name = Column(Unicode(120))
    user_email = Column(Unicode(120))
    user_password = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    user_about = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    user_cdate = Column(DateTime)
    user_llogin = Column(DateTime)
    user_super = Column(INTEGER, server_default=text("'0'"))
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    user_active = Column(INTEGER, server_default=text("'1'"))
    user_apikey = Column(Unicode(64))
    user_apisecret = Column(Unicode(64))
    user_apitoken = Column(Unicode(64))
    user_apitoken_expires_on = Column(DateTime)
    user_query_user = Column(Unicode(64))
    user_query_password = Column(Unicode(256))

    user_password_reset_key = Column(Unicode(64))
    user_password_reset_token = Column(Unicode(64))
    user_password_reset_expires_on = Column(DateTime)

    user_timezone = Column(
        ForeignKey("timezone.timezone_code", ondelete="RESTRICT"),
        nullable=False,
        server_default=text("'UTC'"),
    )

    timezone = relationship("TimeZone")


class Project(Base):
    __tablename__ = "project"

    project_id = Column(Unicode(64), primary_key=True)
    project_code = Column(Unicode(45))
    project_name = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    project_abstract = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    project_cdate = Column(DateTime)
    project_public = Column(INTEGER)
    project_image = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    project_case = Column(INTEGER, server_default=text("'0'"))
    project_icon = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    project_formlist_auth = Column(INTEGER, server_default=text("'1'"))
    project_hexcolor = Column(Unicode(60))
    project_timezone = Column(
        ForeignKey("timezone.timezone_code", ondelete="RESTRICT"),
        nullable=False,
        server_default=text("'UTC'"),
    )
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    timezone = relationship("TimeZone")


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

    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    coll_id = Column(Unicode(120), primary_key=True, nullable=False)
    coll_name = Column(Unicode(120))
    coll_password = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    coll_active = Column(INTEGER)
    coll_cdate = Column(DateTime)
    coll_email = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    coll_telephone = Column(Unicode(120))
    coll_prjshare = Column(INTEGER)
    coll_apikey = Column(Unicode(64))
    coll_apisecret = Column(Unicode(64))
    coll_apitoken = Column(Unicode(64))
    coll_apitoken_expires_on = Column(DateTime)
    coll_query_user = Column(Unicode(64))
    coll_query_password = Column(Unicode(256))
    coll_timezone = Column(
        ForeignKey("timezone.timezone_code", ondelete="RESTRICT"),
        nullable=False,
        server_default=text("'UTC'"),
    )
    extras = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    tags = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))

    project = relationship("Project")
    timezone = relationship("TimeZone")


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
        ForeignKey("project.project_id", ondelete="CASCADE"),
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
    form_public = Column(INTEGER)
    form_geopoint = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_hexcolor = Column(Unicode(60))
    form_reptask = Column(Unicode(64))
    form_index = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    form_type = Column(INTEGER, server_default=text("'1'"))
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
        ForeignKey("fsuser.user_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
        index=True,
    )
    access_type = Column(
        INTEGER
    )  # 1=Owner,2=Admin,3=Editor,4=Member. Note: 5=Public access (Set internally)
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
            ["enum_project", "coll_id"],
            ["collaborator.project_id", "collaborator.coll_id"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["project_id", "group_id"],
            ["collgroup.project_id", "collgroup.group_id"],
            ondelete="CASCADE",
        ),
        Index("fk_enumingroup_enumerator1_idx", "enum_project", "coll_id"),
        Index("fk_enumingroup_enumerator1", "enum_project", "coll_id"),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    group_id = Column(Unicode(12), primary_key=True, nullable=False)
    enum_project = Column(Unicode(64), primary_key=True, nullable=False)
    coll_id = Column(Unicode(120), primary_key=True, nullable=False)
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
            ["project_id", "coll_id"],
            ["collaborator.project_id", "collaborator.coll_id"],
            ondelete="CASCADE",
        ),
        Index("fk_submitter_form1_idx", "form_project", "form_id"),
        Index("fk_submitter_form1", "form_project", "form_id"),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    coll_id = Column(Unicode(120), primary_key=True, nullable=False)
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
            ["enum_project", "coll_id"],
            ["collaborator.project_id", "collaborator.coll_id"],
        ),
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
        Index("fk_jsonlog_form1_idx", "project_id", "form_id"),
        Index("fk_jsonlog_enumerator1_idx", "enum_project", "coll_id"),
    )

    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    log_id = Column(Unicode(64), primary_key=True, nullable=False)
    log_dtime = Column(DateTime)
    json_file = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    log_file = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    command_executed = Column(MEDIUMTEXT(collation="utf8mb4_unicode_ci"))
    status = Column(INTEGER)
    enum_project = Column(Unicode(64), nullable=True)
    coll_id = Column(Unicode(120), nullable=True)

    collaborator = relationship("Collaborator")
    project = relationship("Odkform")


class Submission(Base):
    __tablename__ = "submission"
    __table_args__ = (
        ForeignKeyConstraint(
            ["enum_project", "coll_id"],
            ["collaborator.project_id", "collaborator.coll_id"],
        ),
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
        Index("fk_submission_enumerator1_idx", "enum_project", "coll_id"),
        Index("fk_submission_form1_idx", "project_id", "form_id"),
    )

    project_id = Column(Unicode(64), primary_key=True, nullable=False)
    form_id = Column(Unicode(120), primary_key=True, nullable=False)
    submission_id = Column(Unicode(64), primary_key=True, nullable=False)
    submission_dtime = Column(DateTime)
    submission_status = Column(INTEGER)
    enum_project = Column(Unicode(64), nullable=True)
    coll_id = Column(Unicode(120), nullable=True)
    md5sum = Column(Unicode(120))
    original_md5sum = Column(Unicode(120))
    sameas = Column(Unicode(64))

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
            ["enum_project", "coll_id"],
            ["collaborator.project_id", "collaborator.coll_id"],
        ),
        ForeignKeyConstraint(
            ["form_id", "project_id", "log_id"],
            ["jsonlog.form_id", "jsonlog.project_id", "jsonlog.log_id"],
            ondelete="CASCADE",
        ),
        Index("fk_jsonhistory_enumerator1_idx", "enum_project", "coll_id"),
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
    enum_project = Column(Unicode(64), nullable=False)
    coll_id = Column(Unicode(120), nullable=False)

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
    field_size = Column(INTEGER, server_default=text("'0'"))
    field_decsize = Column(INTEGER, server_default=text("'0'"))
    field_sensitive = Column(INTEGER, server_default=text("'0'"))
    field_protection = Column(Unicode(64))

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
