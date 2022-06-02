import datetime
import time
import uuid

from .sql import get_partner_api_key, get_form_details, get_one_submission


def t_e_s_t_partners(test_object):
    # show the partner page goes to 404
    test_object.testapp.get(
        "/user/{}/manage_partners".format(test_object.collaboratorLogin),
        status=404,
    )

    # show the partner page
    test_object.testapp.get(
        "/user/{}/manage_partners".format(test_object.randonLogin),
        status=200,
    )

    # Add new the partner page
    test_object.testapp.get(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        status=200,
    )

    # Add a new partner fail. Empty email
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_email": "",
            "partner_name": "",
            "partner_organization": "",
            "partner_telephone": "",
            "partner_password": "",
            "partner_password2": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add a new partner fail. Invalid email
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_email": "cquiros~qlands.com",
            "partner_name": "",
            "partner_organization": "",
            "partner_telephone": "",
            "partner_password": "",
            "partner_password2": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add partner pass
    partner_id = str(uuid.uuid4())
    partner = partner_id[-12:]
    test_object.partner = partner

    # Add a new partner fail. Empty organization
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos Quiros",
            "partner_organization": "",
            "partner_telephone": "",
            "partner_password": "123",
            "partner_password2": "123",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add a new partner fail. Empty name
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "",
            "partner_organization": "QLands",
            "partner_telephone": "",
            "partner_password": "123",
            "partner_password2": "123",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add a new partner fail. Empty telephone
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos Quiros",
            "partner_organization": "QLands",
            "partner_telephone": "",
            "partner_password": "123",
            "partner_password2": "123",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add a new partner fail. Empty password
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos Quiros",
            "partner_organization": "QLands",
            "partner_telephone": "22390771",
            "partner_password": "",
            "partner_password2": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Add a new partner fail. Empty password not the same
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos Quiros",
            "partner_organization": "QLands",
            "partner_telephone": "22390771",
            "partner_password": "123",
            "partner_password2": "321",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    print("Partner ID: {}".format(partner_id))
    print("Partner email: e{}@qlands.com".format(partner))
    print("Partner working with login: {}".format(test_object.randonLogin))
    print("Partner working with project: {}".format(test_object.project))
    print("Partner working with form: {}".format(test_object.formID))
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_id": partner_id,
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos Quiros",
            "partner_organization": "QLands",
            "partner_telephone": "22390771",
            "partner_password": "123",
            "partner_password2": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Second partner  pass
    partner_id2 = str(uuid.uuid4())
    partner2 = partner_id2[-12:]
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_id": partner_id2,
            "partner_email": "e{}@qlands.com".format(partner2),
            "partner_name": "Carlos Quiros",
            "partner_organization": "QLands",
            "partner_telephone": "22390771",
            "partner_password": "123",
            "partner_password2": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add a new partner fail. Partner already exists
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos Quiros",
            "partner_organization": "QLands",
            "partner_telephone": "22390771",
            "partner_password": "123",
            "partner_password2": "123",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Show modify partner
    res = test_object.testapp.get(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, partner_id),
        status=200,
    )
    test_object.root.assertNotIn(b"This partner was created", res.body)

    # Modify partner fail. Organization is empty
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, partner_id),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos Quiros",
            "partner_organization": "",
            "partner_telephone": "22390771",
            "partner_apikey": "123",
            "modify": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Modify partner fail. Name is empty
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, partner_id),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "",
            "partner_organization": "QLandds",
            "partner_telephone": "22390771",
            "partner_apikey": "123",
            "modify": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Modify partner fail. Telephone is empty
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, partner_id),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos",
            "partner_organization": "QLandds",
            "partner_telephone": "",
            "partner_apikey": "123",
            "modify": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Modify partner fail. Email is invalid
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, partner_id),
        {
            "partner_email": "cquiros~qlands.com".format(partner),
            "partner_name": "Carlos",
            "partner_organization": "QLandds",
            "partner_telephone": "22390771",
            "partner_apikey": "123",
            "modify": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Modify partner fail. Email is already taken
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, partner_id),
        {
            "partner_email": "e{}@qlands.com".format(partner2),
            "partner_name": "Carlos",
            "partner_organization": "QLandds",
            "partner_telephone": "22390771",
            "partner_apikey": "123",
            "modify": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Modify partner pass that does not exist goes to 404.
    test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, "not_here"),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos",
            "partner_organization": "QLandds",
            "partner_telephone": "63554488",
            "partner_apikey": "123",
            "modify": "",
        },
        status=404,
    )

    # Test logout
    test_object.testapp.get("/logout", status=302)

    # Login succeed by collaborator
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.collaboratorLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Modify partner fails. Collaborator has no access
    test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(
            test_object.collaboratorLogin, partner_id
        ),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos",
            "partner_organization": "QLandds",
            "partner_telephone": "63554488",
            "partner_apikey": "123",
            "modify": "",
        },
        status=404,
    )

    # Test logout
    test_object.testapp.get("/logout", status=302)

    # Login succeed by collaborator
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Modify partner pass.
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, partner_id),
        {
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos",
            "partner_organization": "QLandds",
            "partner_telephone": "63554488",
            "partner_apikey": "123",
            "modify": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change password fails. Empty pass
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, partner_id),
        {
            "partner_password": "",
            "partner_password2": "",
            "changepass": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Change password fails. Not same pass
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, partner_id),
        {
            "partner_password": "123",
            "partner_password2": "",
            "changepass": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Change password pass
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(test_object.randonLogin, partner_id),
        {
            "partner_password": "123",
            "partner_password2": "123",
            "changepass": "",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Delete partner that does not exist goes to 404.
    test_object.testapp.post(
        "/user/{}/manage_partner/{}/delete".format(test_object.randonLogin, "not_here"),
        {},
        status=404,
    )

    # Delete partners with get goes to 404
    test_object.testapp.get(
        "/user/{}/manage_partner/{}/delete".format(test_object.randonLogin, partner_id),
        status=404,
    )

    # Delete partner passes
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/delete".format(test_object.randonLogin, partner_id),
        {},
        status=302,
    )
    assert "FS_error" not in res.headers
    test_object.root.assertNotIn(b"This partner was created", res.body)

    time.sleep(10)  # Wait for ES to remove the partner

    # Add partner again
    res = test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLogin),
        {
            "partner_id": partner_id,
            "partner_email": "e{}@qlands.com".format(partner),
            "partner_name": "Carlos Quiros",
            "partner_organization": "QLands",
            "partner_telephone": "22390771",
            "partner_password": "123",
            "partner_password2": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add partner using other user goes tot 404
    test_object.testapp.post(
        "/user/{}/manage_partners/add".format(test_object.randonLoginPartner),
        {},
        status=404,
    )

    # Edit partner using other use goes to 4-4
    test_object.testapp.post(
        "/user/{}/manage_partner/{}/edit".format(
            test_object.randonLoginPartner, partner_id
        ),
        {},
        status=404,
    )

    # Delete partner using other account goes to 404
    test_object.testapp.post(
        "/user/{}/manage_partner/{}/delete".format(
            test_object.randonLoginPartner, partner_id
        ),
        {},
        status=404,
    )

    # Logout
    res = test_object.testapp.post(
        "/logout",
        status=302,
    )
    assert "FS_error" not in res.headers

    # Login succeed random login partner
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLoginPartner, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Random login partner cannot edit partner
    res = test_object.testapp.get(
        "/user/{}/manage_partner/{}/edit".format(
            test_object.randonLoginPartner, partner_id
        ),
        status=200,
    )
    test_object.root.assertIn(b"This partner was created", res.body)

    # Random login partner cannot delete partner
    res = test_object.testapp.post(
        "/user/{}/manage_partner/{}/delete".format(
            test_object.randonLoginPartner, partner_id
        ),
        {},
        status=302,
    )
    assert "FS_error" in res.headers

    # Logout
    res = test_object.testapp.post(
        "/logout",
        status=302,
    )
    assert "FS_error" not in res.headers

    # Login succeed random login
    res = test_object.testapp.post(
        "/login",
        {"user": "", "email": test_object.randonLogin, "passwd": "123"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an partner to a project fails. Empty partner
    res = test_object.testapp.post(
        "/user/{}/project/{}/link_partner".format(
            test_object.randonLogin, test_object.project
        ),
        {"partner_id": ""},
        status=302,
    )
    assert "FS_error" in res.headers

    # Add an partner to a project fails. Invalid dates
    res = test_object.testapp.post(
        "/user/{}/project/{}/link_partner".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "",
            "access_to": "",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Add an partner to a project fails. Invalid dates
    res = test_object.testapp.post(
        "/user/{}/project/{}/link_partner".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2021-07-05",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    test_object.testapp.post(
        "/user/{}/project/{}/link_partner".format(test_object.randonLogin, "not_exist"),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2021-08-05",
        },
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/link_partner".format(
            test_object.randonLogin, test_object.project
        ),
        status=404,
    )

    # Add an partner to project pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/link_partner".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2021-08-05",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an partner to a project fails. Partner already linked
    res = test_object.testapp.post(
        "/user/{}/project/{}/link_partner".format(
            test_object.randonLogin, test_object.project
        ),
        {"partner_id": partner_id},
        status=302,
    )
    assert "FS_error" in res.headers

    # Edit partner project options fails. Invalid dates
    res = test_object.testapp.post(
        "/user/{}/project/{}/edit_partner/{}".format(
            test_object.randonLogin, test_object.project, partner_id
        ),
        {
            "time_bound": 1,
            "access_from": "",
            "access_to": "",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Edit partner project options fails. Invalid dates
    res = test_object.testapp.post(
        "/user/{}/project/{}/edit_partner/{}".format(
            test_object.randonLogin, test_object.project, partner_id
        ),
        {
            "time_bound": 1,
            "access_from": "2021-08-19",
            "access_to": "2021-07-19",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    test_object.testapp.post(
        "/user/{}/project/{}/edit_partner/{}".format(
            test_object.randonLogin, "not_exist", partner_id
        ),
        {
            "time_bound": 1,
            "access_from": "2021-08-19",
            "access_to": "2021-10-19",
        },
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/edit_partner/{}".format(
            test_object.randonLogin, test_object.project, partner_id
        ),
        status=404,
    )

    # Edit partner project options pass.
    res = test_object.testapp.post(
        "/user/{}/project/{}/edit_partner/{}".format(
            test_object.randonLogin, test_object.project, partner_id
        ),
        {
            "time_bound": 1,
            "access_from": "2021-08-19",
            "access_to": "2021-10-19",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Edit partner project options pass. Remove time bound
    res = test_object.testapp.post(
        "/user/{}/project/{}/edit_partner/{}".format(
            test_object.randonLogin, test_object.project, partner_id
        ),
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    test_object.testapp.post(
        "/user/{}/project/{}/remove_partner/{}".format(
            test_object.randonLogin, "not_exist", partner_id
        ),
        {},
        status=404,
    )

    test_object.testapp.get(
        "/user/{}/project/{}/remove_partner/{}".format(
            test_object.randonLogin, test_object.project, partner_id
        ),
        status=404,
    )

    # Remove partner from project passes
    res = test_object.testapp.post(
        "/user/{}/project/{}/remove_partner/{}".format(
            test_object.randonLogin, test_object.project, partner_id
        ),
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an partner to project again pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/link_partner".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2121-08-05",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add partner to a form in a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        {"partner_id": ""},
        status=404,
    )

    # Add partner to a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, "not_exit"
        ),
        {"partner_id": ""},
        status=404,
    )

    # Add partner to a form using get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=404,
    )

    # Add an partner to a form fails. Empty partner
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=302,
    )
    assert "FS_error" in res.headers

    # Add an partner to a form fails. Empty partner
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"partner_id": ""},
        status=302,
    )
    assert "FS_error" in res.headers

    # Add an partner to a form fails. Invalid dates
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "",
            "access_to": "",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Add an partner to a form fails. Invalid dates
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2021-07-05",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Add an partner to form pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2021-08-05",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an partner to a form fails. Partner already linked
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {"partner_id": partner_id},
        status=302,
    )
    assert "FS_error" in res.headers

    # Edit a partner of a form in a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/edit".format(
            test_object.randonLogin, "not_exist", test_object.formID, partner_id
        ),
        {
            "time_bound": 1,
            "access_from": "",
            "access_to": "",
        },
        status=404,
    )

    # Edit a partner of a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/edit".format(
            test_object.randonLogin, test_object.project, "not_exist", partner_id
        ),
        {
            "time_bound": 1,
            "access_from": "",
            "access_to": "",
        },
        status=404,
    )

    # Edit a partner of a form using get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/partner/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.formID, partner_id
        ),
        status=404,
    )

    # Edit partner form options fails. Invalid dates
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.formID, partner_id
        ),
        {
            "time_bound": 1,
            "access_from": "",
            "access_to": "",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Edit partner form options fails. Invalid dates
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.formID, partner_id
        ),
        {
            "time_bound": 1,
            "access_from": "2021-08-19",
            "access_to": "2021-07-19",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Edit partner form options pass.
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.formID, partner_id
        ),
        {
            "time_bound": 1,
            "access_from": "2021-08-19",
            "access_to": "2021-10-19",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Edit partner form options pass. Remove time bound
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/edit".format(
            test_object.randonLogin, test_object.project, test_object.formID, partner_id
        ),
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Remove a partner from a form in a project that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/remove".format(
            test_object.randonLogin, "not_exist", test_object.formID, partner_id
        ),
        {},
        status=404,
    )

    # Remove a partner from a form that does not exist goes to 404
    test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/remove".format(
            test_object.randonLogin, test_object.project, "not_exist", partner_id
        ),
        {},
        status=404,
    )

    # Remove a partner from a form using get goes to 404
    test_object.testapp.get(
        "/user/{}/project/{}/form/{}/partner/{}/remove".format(
            test_object.randonLogin, test_object.project, test_object.formID, partner_id
        ),
        status=404,
    )

    # Remove partner from form passes
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/remove".format(
            test_object.randonLogin, test_object.project, test_object.formID, partner_id
        ),
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an partner to form again pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2121-08-05",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Show the partner login
    test_object.testapp.get(
        "/partneraccess/login",
        status=200,
    )

    # Partner login fails. Partner does not exists
    res = test_object.testapp.post(
        "/partneraccess/login",
        {
            "login": "",
            "passwd": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Partner login fails. Invalid password
    res = test_object.testapp.post(
        "/partneraccess/login",
        {
            "login": "e{}@qlands.com".format(partner),
            "passwd": "",
        },
        status=200,
    )
    assert "FS_error" in res.headers

    # Partner login pass
    res = test_object.testapp.post(
        "/partneraccess/login",
        {
            "login": "e{}@qlands.com".format(partner),
            "passwd": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Go to login redirects to outputs
    test_object.testapp.get(
        "/partneraccess/login",
        status=302,
    )

    # Partner logout pass
    res = test_object.testapp.post(
        "/partneraccess/logout",
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Show the partner login
    test_object.testapp.get(
        "/partneraccess/dashboard",
        status=302,
    )

    # Partner login pass
    res = test_object.testapp.post(
        "/partneraccess/login",
        {
            "login": "e{}@qlands.com".format(partner),
            "passwd": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Show partner outputs. Partner has projects
    res = test_object.testapp.get(
        "/partneraccess/dashboard",
        status=200,
    )
    test_object.root.assertIn(b"data-title", res.body)

    # Change password with get goes to 404
    test_object.testapp.get(
        "/partneraccess/changemypassword",
        {"partner_password": ""},
        status=404,
    )

    # Partner change password fails. Empty password
    res = test_object.testapp.post(
        "/partneraccess/changemypassword",
        {"partner_password": ""},
        status=302,
    )
    assert "FS_error" in res.headers

    # Partner change password fails. Password are not the same
    res = test_object.testapp.post(
        "/partneraccess/changemypassword",
        {"partner_password": "321", "partner_password2": "123"},
        status=302,
    )
    assert "FS_error" in res.headers

    # Partner change password fails. Old password is not correct
    res = test_object.testapp.post(
        "/partneraccess/changemypassword",
        {
            "partner_password": "123",
            "partner_password2": "123",
            "old_password": "some",
        },
        status=302,
    )
    assert "FS_error" in res.headers

    # Partner change password pass
    res = test_object.testapp.post(
        "/partneraccess/changemypassword",
        {
            "partner_password": "123",
            "partner_password2": "123",
            "old_password": "123",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change password with get goes to 404
    test_object.testapp.get(
        "/partneraccess/changemyapikey",
        {"partner_apikey": ""},
        status=404,
    )

    # Partner change API key pass
    partner_api_key = get_partner_api_key(test_object.server_config, partner_id)
    res = test_object.testapp.post(
        "/partneraccess/changemyapikey",
        {"partner_apikey": partner_api_key},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Partner change timezone pass
    res = test_object.testapp.post(
        "/partneraccess/changemytimezone",
        {"partner_timezone": "UTC"},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Change password with get goes to 404
    test_object.testapp.get(
        "/partneraccess/changemytimezone",
        {"partner_timezone": "UTC"},
        status=404,
    )

    # Remove partner from project passes
    res = test_object.testapp.post(
        "/user/{}/project/{}/remove_partner/{}".format(
            test_object.randonLogin, test_object.project, partner_id
        ),
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Remove partner from form passes
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/remove".format(
            test_object.randonLogin, test_object.project, test_object.formID, partner_id
        ),
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Partner does not have projects
    res = test_object.testapp.get(
        "/partneraccess/dashboard",
        status=200,
    )
    test_object.root.assertNotIn(b"data-title", res.body)

    # Add an partner to form again pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "partner_id": partner_id,
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Show partner outputs. Partner has projects through forms
    res = test_object.testapp.get(
        "/partneraccess/dashboard",
        status=200,
    )
    test_object.root.assertIn(b"data-title", res.body)

    # Add an partner to another form in same project
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, "ADANIC_ALLMOD_20141020"
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2121-08-05",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Show partner outputs. Partner has projects through forms
    res = test_object.testapp.get(
        "/partneraccess/dashboard",
        status=200,
    )
    test_object.root.assertIn(b"data-title", res.body)

    # Remove partner from form passes
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/remove".format(
            test_object.randonLogin, test_object.project, test_object.formID, partner_id
        ),
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Remove partner from form passes
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partner/{}/remove".format(
            test_object.randonLogin,
            test_object.project,
            "ADANIC_ALLMOD_20141020",
            partner_id,
        ),
        {},
        status=302,
    )
    assert "FS_error" not in res.headers

    # Add an partner to project again pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/link_partner".format(
            test_object.randonLogin, test_object.project
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2121-08-05",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Show partner outputs. Partner has projects through projects
    res = test_object.testapp.get(
        "/partneraccess/dashboard",
        status=200,
    )
    test_object.root.assertIn(b"data-title", res.body)

    # Add an partner to form again pass
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2121-08-05",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Show partner outputs. Partner has projects through projects and forms
    res = test_object.testapp.get(
        "/partneraccess/dashboard",
        status=200,
    )
    test_object.root.assertIn(b"data-title", res.body)

    # Add an partner to another form in same project
    res = test_object.testapp.post(
        "/user/{}/project/{}/form/{}/partners/add".format(
            test_object.randonLogin, test_object.project, "ADANIC_ALLMOD_20141020"
        ),
        {
            "partner_id": partner_id,
            "time_bound": 1,
            "access_from": "2021-08-05",
            "access_to": "2121-08-05",
        },
        status=302,
    )
    assert "FS_error" not in res.headers

    # Show partner outputs. Partner has projects through projects and forms
    res = test_object.testapp.get(
        "/partneraccess/dashboard",
        status=200,
    )
    test_object.root.assertIn(b"data-title", res.body)

    # Get the partner details of a form
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}".format(
            test_object.randonLogin, "not_exist", test_object.formID
        ),
        status=404,
    )

    # Get the partner GPS info of a project that does not exist goes to 404
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/get/gpspoints".format(
            test_object.randonLogin, "not exist", test_object.formID
        ),
        status=404,
    )

    # Get the partner GPS info of a form that does not exist goes to 404
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/get/gpspoints".format(
            test_object.randonLogin, test_object.project, "not_exist"
        ),
        status=404,
    )

    # Get the partner GPS info of a form
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/get/gpspoints".format(
            test_object.randonLogin, test_object.project, test_object.formID
        ),
        status=200,
    )

    form_details = get_form_details(
        test_object.server_config, test_object.projectID, test_object.formID
    )
    submission_id = get_one_submission(
        test_object.server_config, form_details["form_schema"]
    )

    # Get the partner Marker info for a submission in not exist project goes to 404
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/{}/info".format(
            test_object.randonLogin, "not_exist", test_object.formID, submission_id
        ),
        status=404,
    )

    # Get the partner Marker info for a submission in not exist form goes to 404
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/{}/info".format(
            test_object.randonLogin, test_object.project, "not_exist", submission_id
        ),
        status=404,
    )

    # Get the partner Marker info for a submission
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/{}/info".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            submission_id,
        ),
        status=200,
    )

    # Get the partner Marker info for a submission image
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/{}/media/{}/get".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            submission_id,
            "image001.png",
        ),
        status=200,
    )

    # Get the partner product
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/private_download/{}/output/{}".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            "latest",
        ),
        status=200,
    )

    # Get the partner using API goes to 401. No key
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/api_download/{}/output/{}".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            "latest",
        ),
        status=401,
    )

    # Get the partner using API goes to 401. Wrong key
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/api_download/{}/output/{}?apikey={}".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            "latest",
            "wrongAPIKey",
        ),
        status=401,
    )

    partner_api_key = get_partner_api_key(test_object.server_config, partner_id)
    test_object.testapp.get(
        "/partneraccess/user/{}/project/{}/form/{}/api_download/{}/output/{}?apikey={}".format(
            test_object.randonLogin,
            test_object.project,
            test_object.formID,
            "xlsx_public_export",
            "latest",
            partner_api_key,
        ),
        status=200,
    )

    # Partner history goes to 404
    test_object.testapp.get(
        "/user/{}/manage_partner/{}/activity".format(
            test_object.collaboratorLogin, partner_id
        ),
        status=404,
    )

    # Partner history goes to 404
    test_object.testapp.get(
        "/user/{}/manage_partner/{}/activity".format(
            test_object.randonLogin, "not_exist"
        ),
        status=404,
    )

    # Get the history of a partner
    res = test_object.testapp.get(
        "/user/{}/manage_partner/{}/activity".format(
            test_object.randonLogin, partner_id
        ),
        status=200,
    )
    test_object.root.assertIn(b'"timeline-header"', res.body)

    this_year = datetime.datetime.now().strftime("%Y")
    # Get the history of a partner current year
    res = test_object.testapp.get(
        "/user/{}/manage_partner/{}/activity?year={}".format(
            test_object.randonLogin, partner_id, this_year
        ),
        status=200,
    )
    test_object.root.assertIn(b'"timeline-header"', res.body)

    # Get the history of a partner last year
    res = test_object.testapp.get(
        "/user/{}/manage_partner/{}/activity?year={}".format(
            test_object.randonLogin, partner_id, int(this_year) - 2
        ),
        status=200,
    )
    test_object.root.assertNotIn(b'"timeline-header"', res.body)

    # Get the history of a partner invalid year
    res = test_object.testapp.get(
        "/user/{}/manage_partner/{}/activity?year={}".format(
            test_object.randonLogin, partner_id, "year"
        ),
        status=200,
    )
    test_object.root.assertIn(b'"timeline-header"', res.body)

    # Get the available collaborators
    test_object.testapp.get(
        "/user/{}/api/select2_partners?q={}".format(
            test_object.randonLogin, "@qlands.com"
        ),
        status=200,
    )
    # Get the available collaborators
    test_object.testapp.get(
        "/user/{}/api/select2_partners?q={}".format(test_object.randonLogin, "Carlos"),
        status=200,
    )
    test_object.testapp.get(
        "/user/{}/api/select2_partners?q={}".format(
            test_object.randonLogin, "not_exist"
        ),
        status=200,
    )
    test_object.testapp.get(
        "/user/{}/api/select2_partners".format(test_object.randonLogin)
    )
