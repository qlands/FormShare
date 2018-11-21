from formshare.models import map_from_schema, Odkform, User, Formacces, Collingroup, Formgrpacces
import logging


__all__ = ['get_form_details', 'assistant_has_form', 'get_assistant_forms', 'get_form_directory']

log = logging.getLogger(__name__)


def get_creator_data(request, user):
    res = request.dbsession.query(User).filter(User.user_id == user).first()
    return map_from_schema(res)


def get_form_details(request, project, form):
    res = request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(Odkform.form_id == form).first()
    result = map_from_schema(res)
    result['pubby'] = get_creator_data(request, result['form_pubby'])
    return result


def get_assistant_forms(request, project, assistant):
    forms = []

    # Get all the forms that the user can submit data to and are active
    anum_forms = request.dbsession.query(Odkform).filter(Odkform.project_id == Formacces.form_project).filter(
        Odkform.form_id == Formacces.form_id).filter(Formacces.project_id == project).filter(
        Formacces.coll_id == assistant).filter(Formacces.form_project == project).filter(
        Formacces.coll_privileges == 1).filter(Odkform.form_accsub == 1).all()

    for aForm in anum_forms:
        forms.append(
            {'project_id': aForm.form_project, 'form_id': aForm.form_id, 'form_directory': aForm.form_directory})

    # Select the groups that user belongs to
    groups = request.dbsession.query(Collingroup).filter(Collingroup.project_id == project).filter(
        Collingroup.enum_project == project).filter(Collingroup.coll_id == assistant).all()

    for group in groups:
        anum_forms = request.dbsession.query(Odkform).filter(Odkform.project_id == Formgrpacces.form_project).filter(
            Odkform.form_id == Formgrpacces.form_id).filter(Formgrpacces.project_id == group.project_id).filter(
            Formgrpacces.group_id == group.group_id).filter(Formgrpacces.group_privileges == 1).filter(
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


def assistant_has_form(request, project, form, assistant):
    forms = get_assistant_forms(request, project, assistant)
    found = False
    for cform in forms:
        if cform["project_id"] == project and cform["form_id"] == form:
            found = True
            break
    return found


def get_form_directory(request, project, form):
    form_data = request.dbsession.query(Odkform).filter(Odkform.project_id == project).filter(
        Odkform.form_id == form).one()
    form_directory = form_data.form_directory
    return form_directory
