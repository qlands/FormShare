import os


def t_e_s_t_disable_ssl():
    from formshare.scripts.disablessl import main as disablessl

    here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
    paths2 = ["development.ini"]
    ini_file = os.path.join(here, *paths2)

    res = disablessl(["/not_found/development.ini"])
    assert res == 1

    res = disablessl([ini_file])
    assert res == 0
