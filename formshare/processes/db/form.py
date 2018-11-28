from formshare.models import map_from_schema, Odkform, User, Collingroup, Formgrpacces, map_to_schema, \
    MediaFile, Formacces, Collaborator, Collgroup
import logging
from sqlalchemy.exc import IntegrityError
import uuid
import datetime
import mimetypes
from lxml import etree
from formshare.processes.db.assistant import get_project_from_assistant
from sqlalchemy import or_


__all__ = ['get_form_details', 'assistant_has_form', 'get_assistant_forms', 'get_form_directory', 'add_new_form',
           'form_exists', 'get_form_xml_file', 'get_form_xls_file', 'update_form', 'get_form_data', 'get_form_schema',
           'delete_form', 'add_file_to_form', 'get_form_files', 'remove_file_from_form', 'get_url_from_file',
           'form_file_exists', 'update_file_info', 'set_file_with_error', 'add_assistant_to_form',
           'get_form_assistants', 'update_assistant_privileges', 'remove_assistant_from_form', 'add_group_to_form',
           'get_form_groups', 'update_group_privileges', 'remove_group_from_form', 'get_project_forms']

log = logging.getLogger(__name__)


def get_creator_data(request, user):
    res = request.dbsession.query(User).filter(User.user_id == user).first()
    return map_from_schema(res)


def get_form_data(request, project, form):
    res = request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(Odkform.form_id == form).first()
    if res is not None:
        return map_from_schema(res)
    else:
        return None


def get_form_details(request, project, form):
    result = get_form_data(request, project, form)
    if result is not None:
        result['pubby'] = get_creator_data(request, result['form_pubby'])
        return result
    else:
        return None


def get_project_forms(request, project):
    # Get all just parent forms in descending order
    res = request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(
        Odkform.form_incversion == 0).order_by(Odkform.form_cdate.desc()).all()
    parent_forms = map_from_schema(res)
    # We nest the forms in an element tree so child belong to parents
    root = etree.Element("root")
    for form in parent_forms:
        e_form = etree.Element(form['form_id'])
        e_form.set("haschildren", "False")
        root.append(e_form)

    # Get all children forms in ascending order
    res = request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(
        Odkform.form_incversion == 1).order_by(Odkform.form_cdate.asc()).all()
    child_forms = map_from_schema(res)
    for form in child_forms:
        form_id = root.findall(".//" + form['parent_form'])
        if form_id:
            form_id[0].set("haschildren", "True")
            form_id[0].append(etree.Element(form['form_id']))

    # Get all the form ids in order
    form_order = []
    for tag in root.iter():
        if tag.tag != "root":
            form_order.append({'id': tag.tag, 'haschildren': tag.get("haschildren")})

    # Get all the forms in order
    all_forms = parent_forms + child_forms
    forms = []
    for form in form_order:
        for a_form in all_forms:
            if form['id'] == a_form['form_id']:
                a_form['haschildren'] = form['haschildren']
                forms.append(a_form)
                break

    for form in forms:
        form['pubby'] = get_creator_data(request, form['form_pubby'])

    return forms


def get_assistant_forms(request, requested_project, assistant_project, assistant):
    forms = []
    # Get all the forms that the user can submit data to and are active
    anum_forms = request.dbsession.query(Odkform).filter(Odkform.project_id == Formacces.form_project).filter(
        Odkform.form_id == Formacces.form_id).filter(Formacces.project_id == assistant_project).filter(
        Formacces.coll_id == assistant).filter(Formacces.form_project == requested_project).filter(
        or_(Formacces.coll_privileges == 1, Formacces.coll_privileges == 3)).filter(Odkform.form_accsub == 1).all()

    for aForm in anum_forms:
        forms.append(
            {'project_id': aForm.project_id, 'form_id': aForm.form_id, 'form_directory': aForm.form_directory})

    # Select the groups that user belongs to
    groups = request.dbsession.query(Collingroup).filter(Collingroup.project_id == requested_project).filter(
        Collingroup.enum_project == assistant_project).filter(Collingroup.coll_id == assistant).all()

    for group in groups:
        anum_forms = request.dbsession.query(Odkform).filter(Odkform.project_id == Formgrpacces.form_project).filter(
            Odkform.form_id == Formgrpacces.form_id).filter(Formgrpacces.project_id == group.project_id).filter(
            Formgrpacces.group_id == group.group_id).filter(
            or_(Formgrpacces.group_privileges == 1, Formgrpacces.group_privileges == 3)).filter(
            Odkform.form_accsub == 1).all()

        # Append only new forms accessible by the groups of the assistant
        for aForm in anum_forms:
            found = False
            for cform in forms:
                if cform["project_id"] == aForm.project_id and cform["form_id"] == aForm.form_id:
                    found = True
                    break
            if not found:
                forms.append(
                    {'project_id': aForm.project_id, 'form_id': aForm.form_id, 'form_directory': aForm.form_directory})

    return forms


def assistant_has_form(request, user, project, form, assistant):
    assistant_project = get_project_from_assistant(request, user, project, assistant)
    forms = get_assistant_forms(request, project, assistant_project, assistant)
    found = False
    for cform in forms:
        if cform["project_id"] == project and cform["form_id"] == form:
            found = True
            break
    return found


def get_form_directory(request, project, form):
    form_data = request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(
        Odkform.form_id == form).one()
    if form_data is not None:
        return form_data.form_directory
    else:
        return None


def get_form_xml_file(request, project, form):
    form_data = request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(
        Odkform.form_id == form).one()
    if form_data is not None:
        return form_data.form_xmlfile
    else:
        return None


def get_form_xls_file(request, project, form):
    form_data = request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(
        Odkform.form_id == form).one()
    if form_data is not None:
        return form_data.form_xlsfile
    else:
        return None


def get_form_schema(request, project, form):
    form_data = request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(
        Odkform.form_id == form).one()
    if form_data is not None:
        return form_data.form_schema
    else:
        return None


def get_form_files(request, project, form):
    files = request.dbsession.query(MediaFile).filter(MediaFile.project_id == project).filter(
        MediaFile.form_id == form).all()
    return map_from_schema(files)


def add_new_form(request, form_data):
    mapped_data = map_to_schema(Odkform, form_data)
    new_form = Odkform(**mapped_data)
    try:
        request.dbsession.add(new_form)
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        request.dbsession.rollback()
        return False, str(e)
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while adding a new form".format(str(e)))
        return False, str(e)


def form_exists(request, project, form):
    res = request.dbsession.query(Odkform).filter(Odkform.form_id == form).filter(Odkform.project_id == project).first()
    if res is None:
        return False
    else:
        return True


def update_form(request, project, form, form_data):
    mapped_data = map_to_schema(Odkform, form_data)
    try:
        request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(Odkform.form_id == form).update(
            mapped_data)
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        request.dbsession.rollback()
        return False, str(e)
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while updating form {} in project {}".format(str(e), project, form))
        return False, str(e)


def delete_form(request, project, form):
    try:
        request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(Odkform.form_id == form).delete()
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        request.dbsession.rollback()
        return False, str(e)
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while updating form {} in project {}".format(str(e), project, form))
        return False, str(e)


def add_file_to_form(request, project, form, file_name, file_url=None, overwrite=False, md5sum=None):
    res = request.dbsession.query(MediaFile).filter(MediaFile.project_id == project).filter(
        MediaFile.form_id == form).filter(MediaFile.file_name == file_name).first()
    if res is None:
        new_file_id = str(uuid.uuid4())
        content_type, content_enc = mimetypes.guess_type(file_name)
        if content_type is None:
            content_type = 'application/binary'
        new_file = MediaFile(file_id=new_file_id, project_id=project, form_id=form, file_name=file_name,
                             file_udate=datetime.datetime.now(), file_url=file_url, file_md5=md5sum,
                             file_mimetype=content_type)
        try:
            request.dbsession.add(new_file)
            request.dbsession.flush()

        except Exception as e:
            log.error("Error {} while adding file {} in "
                      "form {} of project {} ".format(str(e), file_name, form, project))
            return False, str(e)
        return True, new_file_id
    else:
        if not overwrite:
            return False, request.translate("The file {} already exist".format(file_name))
        else:
            try:
                request.dbsession.query(MediaFile).filter(MediaFile.project_id == project).filter(
                    MediaFile.form_id == form).filter(MediaFile.file_name == file_name).update({'file_md5': md5sum})
                request.dbsession.flush()
            except Exception as e:
                log.error(
                    "Error {} while adding file {} in form {} of project {} ".format(str(e), file_name, form, project))
                return False, str(e)
            return True, ""


def remove_file_from_form(request, project, form, file_name):
    try:
        request.dbsession.query(MediaFile).filter(MediaFile.project_id == project).filter(
            MediaFile.form_id == form).filter(MediaFile.file_name == file_name).delete()
        request.dbsession.flush()
    except Exception as e:
        log.error(
            "Error {} while deleting file {} in form {} of project {} ".format(str(e), file_name, form, project))
        return False, str(e)
    return True, ""


def form_file_exists(request, project, form, file_name):
    res = request.dbsession.query(MediaFile).filter(MediaFile.project_id == project).filter(
        MediaFile.form_id == form).filter(MediaFile.file_name == file_name).first()
    if res is not None:
        return True
    else:
        return False


def get_url_from_file(request, project, form, file_name):
    res = request.dbsession.query(MediaFile).filter(MediaFile.project_id == project).filter(
        MediaFile.form_id == form).filter(MediaFile.file_name == file_name).first()
    if res is not None:
        return res.file_url, res.file_lstdwnld
    else:
        return None, None


def update_file_info(request, project, form, file_name, md5sum, download_datetime=datetime.datetime.now()):
    try:
        request.dbsession.query(MediaFile).filter(MediaFile.project_id == project).filter(
            MediaFile.form_id == form).filter(MediaFile.file_name == file_name).update(
            {'file_lstdwnld': download_datetime, 'file_dwnlderror': 0, 'file_md5': md5sum})
        request.dbsession.flush()
    except Exception as e:
        log.error("Error {} while updating datetime in file {} in form {} of project {} ".format(str(e),
                                                                                                 file_name, form,
                                                                                                 project))
        return False, str(e)
    return True, ""


def set_file_with_error(request, project, form, file_name):
    try:
        request.dbsession.query(MediaFile).filter(MediaFile.project_id == project).filter(
            MediaFile.form_id == form).filter(MediaFile.file_name == file_name).update(
            {'file_dwnlderror': 1})
        request.dbsession.flush()
    except Exception as e:
        log.error(
            "Error {} while updating error in file {} in form {} of project {} ".format(str(e), file_name, form,
                                                                                        project))
        return False, str(e)
    return True, ""


def add_assistant_to_form(request, project, form, from_project, assistant, privilege):
    try:
        new_access = Formacces(project_id=from_project, coll_id=assistant, form_project=project, form_id=form,
                               coll_privileges=privilege, access_date=datetime.datetime.now())
        request.dbsession.add(new_access)
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        log.error("Error {} while adding access to assistant {} of "
                  "project {} to form {} in project {}".format(str(e), assistant, from_project, project, form))
        request.dbsession.rollback()
        return False, "The assistant already exists in this form"
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while adding access to assistant {} of "
                  "project {} to form {} in project {}".format(str(e), assistant, from_project, project, form))
        return False, str(e)


def get_form_assistants(request, project, form):
    res = request.dbsession.query(Collaborator, Formacces).filter(
        Collaborator.project_id == Formacces.project_id).filter(Collaborator.coll_id == Formacces.coll_id).filter(
        Formacces.form_project == project).filter(Formacces.form_id == form).all()
    mapped_data = map_from_schema(res)
    return mapped_data


def update_assistant_privileges(request, project, form, from_project, assistant, privilege):
    try:
        request.dbsession.query(Formacces).filter(Formacces.project_id == from_project).filter(
            Formacces.coll_id == assistant).filter(Formacces.form_project == project).filter(
            Formacces.form_id == form).update({'coll_privileges': privilege})
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while updating access to assistant {} of "
                  "project {} to form {} in project {}".format(str(e), assistant, from_project, project, form))
        return False, str(e)


def remove_assistant_from_form(request, project, form, from_project, assistant):
    try:
        request.dbsession.query(Formacces).filter(Formacces.project_id == from_project).filter(
            Formacces.coll_id == assistant).filter(Formacces.form_project == project).filter(
            Formacces.form_id == form).delete()
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while removing assistant {} of "
                  "project {} from form {} in project {}".format(str(e), assistant, from_project, project, form))
        return False, str(e)


def add_group_to_form(request, project, form, group, privilege):
    try:
        new_access = Formgrpacces(project_id=project, group_id=group, form_project=project, form_id=form,
                                  group_privileges=privilege, access_date=datetime.datetime.now())
        request.dbsession.add(new_access)
        request.dbsession.flush()
        return True, ""
    except IntegrityError as e:
        log.error("Error {} while adding access to group {} of "
                  "project {} to form {}".format(str(e), group, project, form))
        request.dbsession.rollback()
        return False, "The group already exists in this form"
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while adding access to group {} of "
                  "project {} to form {}".format(str(e), group, project, form))
        return False, str(e)


def get_form_groups(request, project, form):
    res = request.dbsession.query(Collgroup, Formgrpacces).filter(
        Collgroup.project_id == Formgrpacces.project_id).filter(Collgroup.group_id == Formgrpacces.group_id).filter(
        Formgrpacces.form_project == project).filter(Formgrpacces.form_id == form).all()
    mapped_data = map_from_schema(res)
    return mapped_data


def update_group_privileges(request, project, form, group, privilege):
    try:
        request.dbsession.query(Formgrpacces).filter(Formgrpacces.project_id == project).filter(
            Formgrpacces.group_id == group).filter(Formgrpacces.form_project == project).filter(
            Formgrpacces.form_id == form).update({'group_privileges': privilege})
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while updating access to group {} of "
                  "to form {} in project {}".format(str(e), group, project, form))
        return False, str(e)


def remove_group_from_form(request, project, form, group):
    try:
        request.dbsession.query(Formgrpacces).filter(Formgrpacces.project_id == project).filter(
            Formgrpacces.group_id == group).filter(Formgrpacces.form_project == project).filter(
            Formgrpacces.form_id == form).delete()
        request.dbsession.flush()
        return True, ""
    except Exception as e:
        request.dbsession.rollback()
        log.error("Error {} while removing access to group {} of "
                  "to form {} in project {}".format(str(e), group, project, form))
        return False, str(e)
