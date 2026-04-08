import os
import uuid


def t_e_s_t_create_super_user():
    from formshare.scripts.createsuperuser import main as createsuperuser_main

    here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
    paths2 = ["development.ini"]
    ini_file = os.path.join(here, *paths2)

    res = createsuperuser_main(
        [
            ini_file,
        ]
    )
    assert res == 0
