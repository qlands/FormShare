# coding: utf-8
from sqlalchemy import Column, DateTime, ForeignKey, ForeignKeyConstraint, Index, Integer, String, Text
from sqlalchemy.orm import relationship

from .meta import Base

class Datagroup(Base):
    __tablename__ = 'datagroup'
    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'project_id'], [u'project.user_id', u'project.project_id'], ondelete=u'CASCADE'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'},
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    group_id = Column(String(12), primary_key=True, nullable=False)
    group_name = Column(String(120))
    group_desc = Column(Text)
    group_cdate = Column(DateTime)
    group_active = Column(Integer)
    extra = Column(Text)
    tags = Column(Text)

    user = relationship(u'Project')


class Datauser(Base):
    __tablename__ = 'datauser'
    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'project_id'], [u'project.user_id', u'project.project_id'], ondelete=u'CASCADE'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'},
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    duser_id = Column(String(120), primary_key=True, nullable=False)
    user_name = Column(String(120))
    user_password = Column(String(120))
    user_active = Column(Integer)
    user_cdate = Column(DateTime)
    extra = Column(Text)
    tags = Column(Text)

    user = relationship(u'Project')
    users = relationship(u'Datagroup', secondary='useringroup')


class Enumerator(Base):
    __tablename__ = 'enumerator'
    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'project_id'], [u'project.user_id', u'project.project_id'], ondelete=u'CASCADE'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'},
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    enum_id = Column(String(120), primary_key=True, nullable=False)
    enum_name = Column(String(120))
    enum_password = Column(String(120))
    enum_active = Column(Integer)
    enum_cdate = Column(DateTime)
    extra = Column(Text)
    tags = Column(Text)

    user = relationship(u'Project')
    users = relationship(u'Enumgroup', secondary='enumingroup')


class Enumgroup(Base):
    __tablename__ = 'enumgroup'
    __table_args__ = (
        ForeignKeyConstraint(['user_id', 'project_id'], [u'project.user_id', u'project.project_id'], ondelete=u'CASCADE'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'},
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    group_id = Column(String(12), primary_key=True, nullable=False)
    group_name = Column(String(120))
    group_desc = Column(Text)
    group_cdate = Column(DateTime)
    group_active = Column(Integer)
    extra = Column(Text)
    tags = Column(Text)

    user = relationship(u'Project')


class Enumingroup(Base):
    __tablename__ = 'enumingroup'
    __table_args__ = (
        ForeignKeyConstraint(['enum_user', 'enum_project', 'enum_id'], [u'enumerator.user_id', u'enumerator.project_id', u'enumerator.enum_id'], ondelete=u'CASCADE'),
        ForeignKeyConstraint(['user_id', 'project_id', 'group_id'], [u'enumgroup.user_id', u'enumgroup.project_id', u'enumgroup.group_id'], ondelete=u'CASCADE'),
        Index('fk_enumingroup_enumerator1_idx', 'enum_user', 'enum_project', 'enum_id'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'}
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    group_id = Column(String(12), primary_key=True, nullable=False)
    enum_user = Column(String(120), primary_key=True, nullable=False)
    enum_project = Column(String(12), primary_key=True, nullable=False)
    enum_id = Column(String(120), primary_key=True, nullable=False)

    enumerator = relationship(u'Enumerator')
    user = relationship(u'Enumgroup')


class Form(Base):
    __tablename__ = 'form'
    __table_args__ = (
        ForeignKeyConstraint(['parent_user', 'parent_project', 'parent_form'], [u'form.user_id', u'form.project_id', u'form.form_id']),
        ForeignKeyConstraint(['user_id', 'project_id'], [u'project.user_id', u'project.project_id'], ondelete=u'CASCADE'),
        Index('fk_form_form1_idx', 'parent_user', 'parent_project', 'parent_form'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'}
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)
    form_name = Column(String(120))
    form_about = Column(Text)
    form_cdate = Column(DateTime)
    form_directory = Column(String(120))
    form_accsub = Column(Integer)
    form_public = Column(Integer)
    extra = Column(Text)
    tags = Column(Text)
    parent_user = Column(String(120))
    parent_project = Column(String(12))
    parent_form = Column(String(120))

    parent = relationship(u'Form', remote_side=[user_id, project_id, form_id])
    user = relationship(u'Project')
    users = relationship(u'Datagroup', secondary='groupaccess')
    users1 = relationship(u'Enumerator', secondary='submitter')
    users2 = relationship(u'Datauser', secondary='useraccess')
    users3 = relationship(u'Enumgroup', secondary='grpsubmitter')


class Groupaccess(Base):
    __tablename__ = 'groupaccess'
    __table_args__ = (
        ForeignKeyConstraint(['form_user', 'form_project', 'form_id'], [u'form.user_id', u'form.project_id', u'form.form_id']),
        ForeignKeyConstraint(['user_id', 'project_id', 'group_id'], [u'datagroup.user_id', u'datagroup.project_id', u'datagroup.group_id'], ondelete=u'CASCADE'),
        Index('fk_groupaccess_form1_idx', 'form_user', 'form_project', 'form_id'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'}
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    group_id = Column(String(12), primary_key=True, nullable=False)
    form_user = Column(String(120), primary_key=True, nullable=False)
    form_project = Column(String(12), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)

    form = relationship(u'Form')
    user = relationship(u'Datagroup')


class Grpsubmitter(Base):
    __tablename__ = 'grpsubmitter'
    __table_args__ = (
        ForeignKeyConstraint(['form_user', 'form_project', 'form_id'], [u'form.user_id', u'form.project_id', u'form.form_id'], ondelete=u'CASCADE'),
        ForeignKeyConstraint(['user_id', 'project_id', 'group_id'], [u'enumgroup.user_id', u'enumgroup.project_id', u'enumgroup.group_id'], ondelete=u'CASCADE'),
        Index('fk_grpsubmitter_form1_idx', 'form_user', 'form_project', 'form_id'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'}
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    group_id = Column(String(12), primary_key=True, nullable=False)
    form_user = Column(String(120), primary_key=True, nullable=False)
    form_project = Column(String(12), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)

    form = relationship(u'Form')
    user = relationship(u'Enumgroup')


class Log(Base):
    __tablename__ = 'log'
    __table_args__ = ({'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'},
    )

    entry_id = Column(String(64), primary_key=True)
    user_id = Column(ForeignKey(u'user.user_id', ondelete=u'CASCADE'), nullable=False, index=True)
    entry_type = Column(Integer)
    entry_info = Column(Text)

    user = relationship(u'User')


class Project(Base):
    __tablename__ = 'project'
    __table_args__ = ({'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'},
                      )

    user_id = Column(ForeignKey(u'user.user_id', ondelete=u'CASCADE'), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    project_name = Column(String(120), nullable=False)
    project_abstract = Column(Text)
    project_cdate = Column(String(45))
    project_creator = Column(String(45))
    project_cremail = Column(String(45))
    project_contact = Column(String(120))
    project_coemail = Column(String(45))
    extra = Column(Text)
    tags = Column(Text)

    user = relationship(u'User')


class Submitter(Base):
    __tablename__ = 'submitter'
    __table_args__ = (
        ForeignKeyConstraint(['form_user', 'form_project', 'form_id'], [u'form.user_id', u'form.project_id', u'form.form_id'], ondelete=u'CASCADE'),
        ForeignKeyConstraint(['user_id', 'project_id', 'enum_id'], [u'enumerator.user_id', u'enumerator.project_id', u'enumerator.enum_id'], ondelete=u'CASCADE'),
        Index('fk_submitter_form1_idx', 'form_user', 'form_project', 'form_id'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'},
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    enum_id = Column(String(120), primary_key=True, nullable=False)
    form_user = Column(String(120), primary_key=True, nullable=False)
    form_project = Column(String(12), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)

    form = relationship(u'Form')
    user = relationship(u'Enumerator')


class User(Base):
    __tablename__ = 'user'
    __table_args__ = ({'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'},
                      )

    user_id = Column(String(120), primary_key=True)
    user_name = Column(String(120))
    user_password = Column(String(120))
    user_email = Column(String(120))
    user_about = Column(Text)
    user_cdate = Column(DateTime)
    user_llogin = Column(DateTime)
    user_super = Column(Integer)
    user_logo = Column(Text)
    extra = Column(Text)
    tags = Column(Text)


class Useraccess(Base):
    __tablename__ = 'useraccess'
    __table_args__ = (
        ForeignKeyConstraint(['form_user', 'form_project', 'form_id'], [u'form.user_id', u'form.project_id', u'form.form_id']),
        ForeignKeyConstraint(['user_id', 'project_id', 'duser_id'], [u'datauser.user_id', u'datauser.project_id', u'datauser.duser_id'], ondelete=u'CASCADE'),
        Index('fk_useraccess_form1_idx', 'form_user', 'form_project', 'form_id'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'}
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    duser_id = Column(String(120), primary_key=True, nullable=False)
    form_user = Column(String(120), primary_key=True, nullable=False)
    form_project = Column(String(12), primary_key=True, nullable=False)
    form_id = Column(String(120), primary_key=True, nullable=False)

    form = relationship(u'Form')
    user = relationship(u'Datauser')


class Useringroup(Base):
    __tablename__ = 'useringroup'
    __table_args__ = (
        ForeignKeyConstraint(['datauser_user', 'datauser_project', 'datauser_id'], [u'datauser.user_id', u'datauser.project_id', u'datauser.duser_id'], ondelete=u'CASCADE'),
        ForeignKeyConstraint(['user_id', 'project_id', 'group_id'], [u'datagroup.user_id', u'datagroup.project_id', u'datagroup.group_id'], ondelete=u'CASCADE'),
        Index('fk_useringroup_datauser1_idx', 'datauser_user', 'datauser_project', 'datauser_id'),
        {'mysql_engine': 'InnoDB', 'mysql_charset': 'utf8'}
    )

    user_id = Column(String(120), primary_key=True, nullable=False)
    project_id = Column(String(12), primary_key=True, nullable=False)
    group_id = Column(String(12), primary_key=True, nullable=False)
    datauser_user = Column(String(120), primary_key=True, nullable=False)
    datauser_project = Column(String(12), primary_key=True, nullable=False)
    datauser_id = Column(String(120), primary_key=True, nullable=False)

    datauser = relationship(u'Datauser')
    user = relationship(u'Datagroup')
