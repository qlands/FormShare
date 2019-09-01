# coding: utf-8
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    INTEGER,
    Index,
    text,
    Unicode,
    UnicodeText,
    TIMESTAMP,
)
from sqlalchemy.orm import relationship
from .meta import Base

metadata = Base.metadata


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
    user_password = Column(Unicode(120))
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
    extras = Column(UnicodeText)
    tags = Column(UnicodeText)


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
    coll_password = Column(Unicode(120))
    coll_active = Column(INTEGER)
    coll_cdate = Column(DateTime)
    coll_email = Column(UnicodeText)
    coll_telephone = Column(Unicode(120))
    coll_prjshare = Column(INTEGER)
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


class FinishedTask(Base):
    __tablename__ = "finishedtask"
    task_id = Column(Unicode(64), primary_key=True, nullable=False)
    task_enumber = Column(INTEGER)
    task_error = Column(UnicodeText)


class Odkform(Base):
    __tablename__ = "odkform"
    __table_args__ = (
        ForeignKeyConstraint(
            ["parent_project", "parent_form"], ["odkform.project_id", "odkform.form_id"]
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
    form_testing = Column(INTEGER, server_default=text("'0'"))
    form_incversion = Column(INTEGER, server_default=text("'0'"))
    parent_project = Column(Unicode(64))
    parent_form = Column(Unicode(120))
    form_stage = Column(INTEGER)
    form_pkey = Column(Unicode(120))
    form_deflang = Column(Unicode(120))
    form_othlangs = Column(UnicodeText)
    form_sepfile = Column(UnicodeText)
    form_xlsfile = Column(UnicodeText)
    form_xmlfile = Column(UnicodeText)
    form_jsonfile = Column(UnicodeText)
    form_reqfiles = Column(UnicodeText)
    form_public = Column(INTEGER)
    form_geopoint = Column(UnicodeText)
    form_hexcolor = Column(Unicode(60))
    form_reptask = Column(Unicode(64))
    form_type = Column(INTEGER, server_default=text("'1'"))
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
    file_mimetype = Column(Unicode(64))

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
    sameas = Column(Unicode(64))

    collaborator = relationship("Collaborator")
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

