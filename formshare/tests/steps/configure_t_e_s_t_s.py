import os


def t_e_s_t_configure_t_e_s_t_s():
    from formshare.scripts.configuretests import main as configuretests_main
    from pathlib import Path

    here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
    paths2 = ["development.ini"]
    ini_file = os.path.join(here, *paths2)

    home = str(Path.home())
    paths2 = ["test_config.json"]
    json_file = os.path.join(home, *paths2)

    res = configuretests_main(["/not_exists", "/not_exists"])
    assert res == 1
    res = configuretests_main([ini_file, "/not_exists"])
    assert res == 1
    res = configuretests_main(["--json_file", json_file, ini_file, here])
    assert res == 0
    assert os.path.exists(json_file)
