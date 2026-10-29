"""Deleting a form (owner, 2026-10-28).

A form is deleted in two parts.

- **The request** (DeleteForm in views/form.py) asks for the form's ID to be
  typed, refuses what cannot be deleted (deletion_refusal), lets the IForm
  plugins refuse, marks the form and its versions inactive, blocked and
  being deleted in one commit (mark_for_deletion), and queues the task.
- **The task** (products/deletion) revokes what is granted on the
  repository, keeps a gzipped dump of it in the form's directory, drops it,
  renames the directories as deleting a form always did, deletes the forms
  from the index and from the database, and calls IFormDeletionProcess once
  for each form deleted. Users cannot cancel it. A task
  that stops leaves the forms as they were marked, with the reason in
  form_deleteerror, and the technical team resumes it on the server
  (resume_form_deletion).

**What goes:** a form with a repository goes with its versions, every form
sharing the repository, as delete_form did; a form in testing goes alone.
Only the newest version can be deleted, as the page has always offered.

**What refuses it, beyond being blocked or busy:** in a longitudinal study,
a form whose cases another form follows up cannot be deleted before that
form: its repository holds foreign keys to this one's (ON DELETE RESTRICT),
and dropping it would fail half way. That covers a published list's
consumers (the case link and the other selects, in any project), a classic
case creator's follow-ups, and any other live repository with a foreign key
into this one. A form whose lists nobody uses still goes after its lists,
as before.
"""

import datetime
import logging

from formshare.models import (
    FinishedTask,
    ListConsumer,
    Odkform,
    Product,
    Project,
    PublishedList,
)
from sqlalchemy import func
from sqlalchemy import text as sqlalchemy_text

log = logging.getLogger("formshare")

# A task that has not finished after this long died with its worker: it no
# longer keeps a form from being deleted
RUNNING_TASK = datetime.timedelta(hours=2)

__all__ = [
    "forms_of_deletion",
    "deletion_refusal",
    "mark_for_deletion",
    "record_deletion_error",
    "forms_being_deleted",
    "form_being_deleted",
]


def forms_of_deletion(session, project, form):
    """The forms a deletion deletes: every form sharing the form's
    repository, or the form alone when it has none. Odkform rows, the form
    first; none when there is no such form."""
    row = (
        session.query(Odkform)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .first()
    )
    if row is None:
        return []
    if not row.form_schema:
        return [row]
    others = (
        session.query(Odkform)
        .filter(Odkform.form_schema == row.form_schema)
        .filter(~((Odkform.project_id == project) & (Odkform.form_id == form)))
        .order_by(Odkform.form_cdate)
        .all()
    )
    return [row] + others


def _named(session, rows, project):
    """Forms as a message names them: their name and ID, and the project's
    code when it is another project's."""
    codes = {}
    names = []
    for a_row in rows:
        name = "{} ({})".format(a_row.form_name or a_row.form_id, a_row.form_id)
        if a_row.project_id != project:
            if a_row.project_id not in codes:
                codes[a_row.project_id] = (
                    session.query(Project.project_code)
                    .filter(Project.project_id == a_row.project_id)
                    .scalar()
                )
            name += " [{}]".format(codes[a_row.project_id] or a_row.project_id)
        names.append(name)
    return ", ".join(sorted(set(names)))


def _running_tasks(session, project, form):
    """How many tasks run on a form: an export, an import, a build or a
    merge that has not finished, started within RUNNING_TASK."""
    return (
        session.query(Product)
        .filter(Product.project_id == project)
        .filter(Product.form_id == form)
        .filter(Product.celery_taskid.notin_(session.query(FinishedTask.task_id)))
        .filter(Product.datetime_added >= datetime.datetime.now() - RUNNING_TASK)
        .count()
    )


def _outside(rows, keys):
    return [a_row for a_row in rows if (a_row.project_id, a_row.form_id) not in keys]


def _list_users(session, project, ids):
    """The forms that select from a list one of these forms feeds: a case
    link or another select. Each has a foreign key to the source."""
    lists = (
        session.query(PublishedList.project_id, PublishedList.list_id)
        .filter(PublishedList.source_project == project)
        .filter(PublishedList.source_form.in_(ids))
        .all()
    )
    users = []
    for list_project, list_id in lists:
        users += (
            session.query(Odkform)
            .join(
                ListConsumer,
                (ListConsumer.consumer_project == Odkform.project_id)
                & (ListConsumer.consumer_form == Odkform.form_id),
            )
            .filter(ListConsumer.list_project == list_project)
            .filter(ListConsumer.list_id == list_id)
            .all()
        )
    return users


def _fed_lists(session, project, ids):
    return [
        a_row[0]
        for a_row in session.query(PublishedList.list_id)
        .filter(PublishedList.source_project == project)
        .filter(PublishedList.source_form.in_(ids))
        .order_by(PublishedList.list_id)
        .all()
    ]


def _classic_followups(session, form_row):
    """The follow-ups of a classic case creator (2021): the project's other
    case forms."""
    if form_row.form_case != 1 or form_row.form_casetype != 1:
        return []
    return (
        session.query(Odkform)
        .filter(Odkform.project_id == form_row.project_id)
        .filter(Odkform.form_case == 1)
        .filter(Odkform.form_casetype > 1)
        .all()
    )


def _referring_forms(session, schema):
    """The forms whose repository has a foreign key into this one: what the
    database would refuse to drop."""
    schemas = [
        a_row[0]
        for a_row in session.execute(
            sqlalchemy_text(
                "SELECT DISTINCT TABLE_SCHEMA FROM information_schema.KEY_COLUMN_USAGE "
                "WHERE REFERENCED_TABLE_SCHEMA = :schema AND TABLE_SCHEMA <> :schema"
            ),
            {"schema": schema},
        ).fetchall()
    ]
    if not schemas:
        return []
    return session.query(Odkform).filter(Odkform.form_schema.in_(schemas)).all()


def deletion_refusal(request, project, form, forms):
    """Why the form cannot be deleted, in words, or None. forms are those
    the deletion would delete (forms_of_deletion)."""
    _ = request.translate
    session = request.dbsession
    form_row = forms[0]
    keys = {(a_row.project_id, a_row.form_id) for a_row in forms}
    ids = [a_row.form_id for a_row in forms if a_row.project_id == project]
    if any((a_row.form_deleting or 0) != 0 for a_row in forms):
        return _("This form is being deleted")
    newer = (
        session.query(Odkform)
        .filter(Odkform.parent_project == project)
        .filter(Odkform.parent_form == form)
        .first()
    )
    if newer is not None:
        return _(
            "This form has a newer version, {form}. Delete the newest version: it "
            "deletes the older ones with it."
        ).format(form=newer.form_id)
    if any((a_row.form_blocked or 0) != 0 for a_row in forms):
        return _("This form is blocked and cannot be changed at the moment.")
    for a_row in forms:
        if _running_tasks(session, a_row.project_id, a_row.form_id) > 0:
            return _(
                "A task is running on this form: an export, an import, a repository "
                "or a merge. Wait for it to finish, or stop it, and delete the form "
                "then."
            )
    followers = _outside(_list_users(session, project, ids), keys)
    followers += _outside(_classic_followups(session, form_row), keys)
    if followers:
        return _(
            "These forms use the cases this form creates: {forms}. Delete them "
            "first."
        ).format(forms=_named(session, followers, project))
    if form_row.form_schema:
        referring = _outside(_referring_forms(session, form_row.form_schema), keys)
        if referring:
            return _(
                "The repositories of these forms refer to the repository of this "
                "one: {forms}. Delete them first."
            ).format(forms=_named(session, referring, project))
    fed = _fed_lists(session, project, ids)
    if fed:
        return _(
            "This form feeds the published lists {}. Delete the lists first."
        ).format(", ".join(fed))
    return None


def mark_for_deletion(request, project, forms, user):
    """Marks the forms inactive, blocked and being deleted, in one commit,
    unless one of them got blocked or marked in the meantime. Returns whether
    it marked them."""
    keys = [(a_row.project_id, a_row.form_id) for a_row in forms]
    try:
        marked = 0
        for project_id, form_id in keys:
            marked += (
                request.dbsession.query(Odkform)
                .filter(Odkform.project_id == project_id)
                .filter(Odkform.form_id == form_id)
                .filter(func.coalesce(Odkform.form_blocked, 0) == 0)
                .filter(func.coalesce(Odkform.form_deleting, 0) == 0)
                .update(
                    {
                        "form_accsub": 0,
                        "form_blocked": 1,
                        "form_deleting": 1,
                        "form_deletedby": user,
                        "form_deleteerror": None,
                    },
                    synchronize_session=False,
                )
            )
        if marked != len(keys):
            request.dbsession.rollback()
            return False
        request.dbsession.commit()
        return True
    except Exception as e:
        log.error(
            "Error {} while marking form {} of project {} for deletion".format(
                str(e), keys[0][1], project
            )
        )
        request.dbsession.rollback()
        return False


def record_deletion_error(session, keys, message):
    """Says, on the forms being deleted, why their deletion stopped."""
    for project_id, form_id in keys:
        session.query(Odkform).filter(Odkform.project_id == project_id).filter(
            Odkform.form_id == form_id
        ).update({"form_deleteerror": message[:65000]}, synchronize_session=False)
    session.commit()


def form_being_deleted(session, project, form):
    """Whether a form is being deleted. Until it is gone, nothing replaces it
    or adds a version to it: a version made then would go with it, by the
    cascade of its parent's row, and leave its files behind."""
    deleting = (
        session.query(Odkform.form_deleting)
        .filter(Odkform.project_id == project)
        .filter(Odkform.form_id == form)
        .scalar()
    )
    return (deleting or 0) == 1


def forms_being_deleted(session):
    """The forms being deleted, for the technical team: (project id, project
    code, form id, who asked, why it stopped)."""
    return (
        session.query(
            Odkform.project_id,
            Project.project_code,
            Odkform.form_id,
            Odkform.form_deletedby,
            Odkform.form_deleteerror,
        )
        .join(Project, Project.project_id == Odkform.project_id)
        .filter(Odkform.form_deleting == 1)
        .order_by(Project.project_code, Odkform.form_id)
        .all()
    )
