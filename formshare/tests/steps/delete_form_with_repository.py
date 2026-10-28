from .form_deletion import delete_form


def t_e_s_t_delete_form_with_repository(test_object):
    # Delete the form
    res = delete_form(test_object, test_object.project, "ADANIC_ALLMOD_20141020")
