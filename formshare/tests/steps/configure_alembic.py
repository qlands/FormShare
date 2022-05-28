import os


def t_e_s_t_configure_alembic():
    from formshare.scripts.configurealembic import main as configurealembic_main
    from pathlib import Path

    here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
    paths2 = ["development.ini"]
    ini_file = os.path.join(here, *paths2)

    home = str(Path.home())
    paths2 = ["alembic.ini"]
    alembic_file = os.path.join(home, *paths2)

    res = configurealembic_main(["/not_exists", "/not_exists"])
    assert res == 1
    res = configurealembic_main([ini_file, "/not_exists"])
    assert res == 1
    res = configurealembic_main(["--alembic_ini_file", alembic_file, ini_file, here])
    assert res == 0
    assert os.path.exists(alembic_file)
