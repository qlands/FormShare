# coding: utf-8
import json

import sqlalchemy.types as types
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    INTEGER,
    BigInteger,
    Index,
    text,
    Unicode,
    UnicodeText,
)
from sqlalchemy.ext import mutable
from sqlalchemy.orm import relationship

from formshare.models.meta import Base

metadata = Base.metadata


class JsonEncodedDict(types.TypeDecorator):
    """Enables JSON storage by encoding and decoding on the fly."""

    impl = types.UnicodeText

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
    user_password = Column(UnicodeText)
    user_about = Column(UnicodeText)
    user_cdate = Column(DateTime)
    user_llogin = Column(DateTime)
    user_super = Column(INTEGER, server_default=text("'0'"))
    extras = Column(UnicodeText)
    tags = Column(UnicodeText)
    user_active = Column(INTEGER, server_default=text("'1'"))
    user_apikey = Column(Unicode(64))


class Project(Base):
    __tablename__ = "project"

    project_id = Column(Unicode(64), primary_key=True)
    project_code = Column(Unicode(45))
    project_name = Column(UnicodeText)
    project_abstract = Column(UnicodeText)
    project_cdate = Column(DateTime)
    project_public = Column(INTEGER)
    project_image = Column(UnicodeText)
    project_case = Column(INTEGER, server_default=text("'0'"))
    extras = Column(UnicodeText)
    tags = Column(UnicodeText)


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
    coll_password = Column(UnicodeText)
    coll_active = Column(INTEGER)
    coll_cdate = Column(DateTime)
    coll_email = Column(UnicodeText)
    coll_telephone = Column(Unicode(120))
    coll_prjshare = Column(INTEGER)
    coll_apikey = Column(Unicode(64))
    extras = Column(UnicodeText)
    tags = Column(UnicodeText)

    project = relationship("Project")


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
    group_desc = Column(UnicodeText)
    group_cdate = Column(DateTime)
    group_active = Column(INTEGER)
    extras = Column(UnicodeText)
    tags = Column(UnicodeText)

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
    task_error = Column(UnicodeText)


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
    form_othlangs = Column(UnicodeText)
    form_mergetask = Column(Unicode(64))
    form_abletomerge = Column(INTEGER, server_default=text("'-1'"))
    form_repositorypossible = Column(INTEGER, server_default=text("'-1'"))
    form_mergerrors = Column(UnicodeText)
    form_xlsfile = Column(UnicodeText)
    form_xmlfile = Column(UnicodeText)
    form_jsonfile = Column(UnicodeText)
    form_createxmlfile = Column(UnicodeText)
    form_insertxmlfile = Column(UnicodeText)
    form_reqfiles = Column(UnicodeText)
    form_public = Column(INTEGER)
    form_geopoint = Column(UnicodeText)
    form_hexcolor = Column(Unicode(60))
    form_reptask = Column(Unicode(64))
    form_index = Column(UnicodeText)
    form_type = Column(INTEGER, server_default=text("'1'"))
    form_case = Column(INTEGER, server_default=text("'0'"))
    form_casetype = Column(
        INTEGER, server_default=text("'0'")
    )  # 1=Creator, 2= Follow up, 3= Deactivate, 4= Activate
    form_caselabel = Column(Unicode(120))
    form_caseselector = Column(Unicode(120))
    form_caseselectorfilename = Column(Unicode(120))
    form_caseselectorlastgen = Column(DateTime)
    form_hasdictionary = Column(INTEGER, server_default=text("'0'"))
    extras = Column(UnicodeText)
    tags = Column(UnicodeText)

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
    output_file = Column(Unicode(120))
    project_id = Column(Unicode(64), nullable=False)
    form_id = Column(Unicode(120), nullable=False)
    product_id = Column(Unicode(120), nullable=False)
    output_id = Column(Unicode(64), nullable=False)
    output_mimetype = Column(Unicode(120))
    process_only = Column(INTEGER, server_default=text("'0'"))
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


class TaskMessages(Base):
    __tablename__ = "taskmessages"

    message_id = Column(Unicode(64), primary_key=True, nullable=False)
    celery_taskid = Column(
        ForeignKey("product.celery_taskid", ondelete="CASCADE"), nullable=False
    )
    message_date = Column(DateTime)
    message_content = Column(UnicodeText)

    product = relationship("Product")


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
    coll_privileges = Column(INTEGER)
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
    coll_privileges = Column(INTEGER)
    access_date = Column(DateTime)
    extras = Column(UnicodeText)

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
    group_privileges = Column(INTEGER)
    access_date = Column(DateTime)
    extras = Column(UnicodeText)

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
    json_file = Column(UnicodeText)
    log_file = Column(UnicodeText)
    command_executed = Column(UnicodeText)
    status = Column(INTEGER)
    enum_project = Column(Unicode(64), nullable=False)
    coll_id = Column(Unicode(120), nullable=False)

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
    enum_project = Column(Unicode(64), nullable=False)
    coll_id = Column(Unicode(120), nullable=False)
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
    log_notes = Column(UnicodeText)
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
    table_desc = Column(UnicodeText, nullable=False)
    table_lkp = Column(INTEGER, server_default=text("'0'"), nullable=False)
    table_inserttrigger = Column(Unicode(64))
    table_xmlcode = Column(UnicodeText)
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
    field_desc = Column(UnicodeText)
    field_xmlcode = Column(UnicodeText)
    field_type = Column(Unicode(64))
    field_odktype = Column(Unicode(64))
    field_rtable = Column(Unicode(120))
    field_rfield = Column(Unicode(120))
    field_rlookup = Column(INTEGER, server_default=text("'0'"))
    field_key = Column(INTEGER, server_default=text("'0'"))
    field_rname = Column(Unicode(64))
    field_selecttype = Column(INTEGER, server_default=text("'0'"))
    field_externalfilename = Column(UnicodeText)
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
