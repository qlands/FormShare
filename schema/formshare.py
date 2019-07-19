# coding: utf-8
from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    INTEGER,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.mysql.types import TINYINT
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()
metadata = Base.metadata


class Collaboratorlog(Base):
    __tablename__ = "collaboratorlog"

    log_entry = Column(String(64), primary_key=True)
    log_datetime = Column(DateTime)
    access_type = Column(INTEGER(11))
    interface = Column(TINYINT(4))
    action = Column(INTEGER(3))
    userid = Column(String(255))
    org = Column(String(32))
    project = Column(String(32))
    form = Column(String(120))
    collaborator = Column(String(32))
    logid = Column(String(64))
    commitid = Column(String(12))
    schemaid = Column(String(13))
    tableid = Column(String(120))


class Fsuser(Base):
    __tablename__ = "fsuser"

    user_id = Column(String(120), primary_key=True)
    user_name = Column(String(120))
    user_password = Column(String(120))
    user_about = Column(Text)
    user_cdate = Column(DateTime)
    user_llogin = Column(DateTime)
    user_super = Column(INTEGER(11), server_default=text("'0'"))
    extra = Column(Text)
    tags = Column(Text)
    user_active = Column(INTEGER(11), server_default=text("'1'"))
    user_apikey = Column(String(64))


class Project(Base):
    __tablename__ = "project"

    project_id = Column(String(64), primary_key=True)
    project_name = Column(Text)
    project_abstract = Column(Text)
    project_cdate = Column(DateTime)
    project_creator = Column(String(45))
    project_cremail = Column(String(45))
    project_contact = Column(String(120))
    project_coemail = Column(String(45))
    extra = Column(Text)
    tags = Column(Text)


class Userlog(Base):
    __tablename__ = "userlog"

    log_entry = Column(String(64), primary_key=True)
    log_datetime = Column(DateTime)
    access_type = Column(INTEGER(11))
    tableid = Column(String(45))
    action = Column(TINYINT(4))
    userid = Column(String(255))
    org = Column(String(32))
    project = Column(String(32))
    form = Column(String(120))
    collaborator = Column(String(32))
    groupid = Column(String(12))
    septable = Column(String(120))
    sepsection = Column(String(12))
    sepitem = Column(String(120))


class Collaborator(Base):
    __tablename__ = "collaborator"
    __table_args__ = (
        ForeignKeyConstraint(
            ["samas_project", "sameas_coll"],
            ["collaborator.project_id", "collaborator.coll_id"],
            ondelete="CASCADE",
        ),
        Index("fk_enumerator_enumerator1_idx", "samas_project", "sameas_coll"),
    )

    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    coll_id = Column(String(120), primary_key=True, nullable=False)
    coll_name = Column(String(120))
    coll_password = Column(String(120))
    coll_active = Column(INTEGER(11))
    coll_cdate = Column(DateTime)
    coll_email = Column(Text)
    coll_telephone = Column(String(120))
    extra = Column(Text)
    tags = Column(Text)
    samas_project = Column(String(64))
    sameas_coll = Column(String(120))

    project = relationship("Project")
    parent = relationship("Collaborator", remote_side=[project_id, coll_id])


class Collgroup(Base):
    __tablename__ = "collgroup"

    project_id = Column(
        ForeignKey("project.project_id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    )
    group_id = Column(String(12), primary_key=True, nullable=False)
    group_desc = Column(Text)
    group_cdate = Column(DateTime)
    group_active = Column(INTEGER(11))
    extra = Column(Text)
    tags = Column(Text)

    project = relationship("Project")


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
    form_id = Column(String(120), primary_key=True, nullable=False)
    form_name = Column(String(120))
    form_cdate = Column(DateTime)
    form_directory = Column(String(120))
    form_schema = Column(String(13))
    form_accsub = Column(INTEGER(11))
    form_testing = Column(INTEGER(11), server_default=text("'0'"))
    form_incversion = Column(INTEGER(11), server_default=text("'0'"))
    parent_project = Column(String(64))
    parent_form = Column(String(120))
    form_stage = Column(INTEGER(11))
    form_pkey = Column(String(120))
    form_deflang = Column(String(120))
    form_yesno = Column(String(120))
    form_othlangs = Column(Text)
    form_sepfile = Column(Text)
    form_xlsfile = Column(Text)
    form_xmlfile = Column(Text)
    extra = Column(Text)
    tags = Column(Text)

    parent = relationship("Odkform", remote_side=[project_id, form_id])
    project = relationship("Project")


class Userproject(Base):
    __tablename__ = "userproject"

    user_id = Column(ForeignKey("fsuser.user_id"), primary_key=True, nullable=False)
    project_id = Column(
        ForeignKey("project.project_id"), primary_key=True, nullable=False, index=True
    )
    access_type = Column(INTEGER(11))
    access_date = Column(DateTime)

    project = relationship("Project")
    user = relationship("Fsuser")


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

    project_id = Column(String(64), primary_key=True, nullable=False)
    group_id = Column(String(12), primary_key=True, nullable=False)
    enum_project = Column(String(64), primary_key=True, nullable=False)
    coll_id = Column(String(120), primary_key=True, nullable=False)
    coll_privileges = Column(INTEGER(11))
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

    project_id = Column(String(64), primary_key=True, nullable=False)
    coll_id = Column(String(120), primary_key=True, nullable=False)
    form_project = Column(String(64), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)
    coll_privileges = Column(INTEGER(11))
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

    project_id = Column(String(64), primary_key=True, nullable=False)
    group_id = Column(String(12), primary_key=True, nullable=False)
    form_project = Column(String(64), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)
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

    form_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(64), primary_key=True, nullable=False)
    log_id = Column(String(64), primary_key=True, nullable=False)
    log_dtime = Column(DateTime)
    json_file = Column(Text)
    log_file = Column(Text)
    status = Column(INTEGER(11))
    enum_project = Column(String(64), nullable=False)
    coll_id = Column(String(120), nullable=False)

    collaborator = relationship("Collaborator")
    project = relationship("Odkform")


class Septable(Base):
    __tablename__ = "septable"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id"],
            ["odkform.project_id", "odkform.form_id"],
            ondelete="CASCADE",
        ),
    )

    project_id = Column(String(64), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)
    table_name = Column(String(120), primary_key=True, nullable=False)
    table_desc = Column(Text)

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

    project_id = Column(String(64), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)
    submission_id = Column(String(64), primary_key=True, nullable=False)
    submission_dtime = Column(DateTime)
    submission_status = Column(INTEGER(11))
    enum_project = Column(String(64), nullable=False)
    coll_id = Column(String(120), nullable=False)
    md5sum = Column(String(120))
    sameas = Column(String(64))

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

    project_id = Column(String(64), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)
    log_id = Column(String(64), primary_key=True, nullable=False)
    log_sequence = Column(String(12), primary_key=True, nullable=False)
    log_dtime = Column(DateTime)
    log_action = Column(INTEGER(11))
    log_commit = Column(String(12))
    log_notes = Column(Text)
    enum_project = Column(String(64), nullable=False)
    coll_id = Column(String(120), nullable=False)

    collaborator = relationship("Collaborator")
    form = relationship("Jsonlog")


class Sepsection(Base):
    __tablename__ = "sepsection"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id", "table_name"],
            ["septable.project_id", "septable.form_id", "septable.table_name"],
            ondelete="CASCADE",
        ),
    )

    project_id = Column(String(64), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)
    table_name = Column(String(120), primary_key=True, nullable=False)
    section_id = Column(String(12), primary_key=True, nullable=False)
    section_name = Column(String(120))
    section_desc = Column(Text)
    section_order = Column(INTEGER(11))

    project = relationship("Septable")


class Sepitem(Base):
    __tablename__ = "sepitems"
    __table_args__ = (
        ForeignKeyConstraint(
            ["project_id", "form_id", "table_name"],
            ["septable.project_id", "septable.form_id", "septable.table_name"],
            ondelete="CASCADE",
        ),
        ForeignKeyConstraint(
            ["section_project", "section_form", "section_table", "section_id"],
            [
                "sepsection.project_id",
                "sepsection.form_id",
                "sepsection.table_name",
                "sepsection.section_id",
            ],
            ondelete="CASCADE",
        ),
        Index(
            "fk_sepitems_sepsection1_idx",
            "section_project",
            "section_form",
            "section_table",
            "section_id",
        ),
    )

    project_id = Column(String(64), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)
    table_name = Column(String(120), primary_key=True, nullable=False)
    item_name = Column(String(120), primary_key=True, nullable=False)
    item_desc = Column(Text)
    item_xmlcode = Column(Text)
    item_notdisplay = Column(INTEGER(11))
    item_order = Column(INTEGER(11))
    section_project = Column(String(64), nullable=False)
    section_form = Column(String(120), nullable=False)
    section_table = Column(String(120), nullable=False)
    section_id = Column(String(12), nullable=False)

    project = relationship("Septable")
    sepsection = relationship("Sepsection")
