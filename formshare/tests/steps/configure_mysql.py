import os


def t_e_s_t_configure_mysql():
    from formshare.scripts.configuremysql import main as configuremysql_main
    from pathlib import Path

    here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
    paths2 = ["development.ini"]
    ini_file = os.path.join(here, *paths2)

    home = str(Path.home())
    paths2 = ["mysql.cnf"]
    mysql_file = os.path.join(home, *paths2)

    res = configuremysql_main(["/not_exists", "/not_exists"])
    assert res == 1
    res = configuremysql_main([ini_file, "/not_exists"])
    assert res == 1
    res = configuremysql_main(["--mysql_cnf_file", mysql_file, ini_file, here])
    assert res == 0
    assert os.path.exists(mysql_file)
