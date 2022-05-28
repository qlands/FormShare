import os
import uuid


def t_e_s_t_create_super_user():
    from formshare.scripts.createsuperuser import main as createsuperuser_main

    here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
    paths2 = ["development.ini"]
    ini_file = os.path.join(here, *paths2)

    random_admin = str(uuid.uuid4())
    random_admin = random_admin[-12:]
    res = createsuperuser_main(
        [
            "--user_id",
            random_admin,
            "--user_email",
            "info@qlandscom",
            "--user_password",
            "123",
            ini_file,
        ]
    )
    assert res == 1
    res = createsuperuser_main(
        [
            "--user_id",
            random_admin,
            "--user_email",
            "{}@qlands.com".format(random_admin),
            "--user_password",
            "123",
            ini_file,
        ]
    )
    assert res == 0
    res = createsuperuser_main(
        [
            "--user_id",
            random_admin,
            "--user_email",
            "{}@qlands.com".format(random_admin),
            "--user_password",
            "123",
            ini_file,
        ]
    )
    assert res == 1
    random_admin2 = str(uuid.uuid4())
    random_admin2 = random_admin2[-12:]
    res = createsuperuser_main(
        [
            "--user_id",
            random_admin2,
            "--user_email",
            "{}@qlands.com".format(random_admin),
            "--user_password",
            "123",
            ini_file,
        ]
    )
    assert res == 1
