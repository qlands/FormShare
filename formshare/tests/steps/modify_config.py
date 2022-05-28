import os
import shutil


def t_e_s_t_modify_config():
    from formshare.scripts.modifyconfig import main as modifyconfig_main
    from pathlib import Path

    here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]
    paths2 = ["development.ini"]
    ini_file = os.path.join(here, *paths2)

    home = str(Path.home())
    paths2 = ["development.ini"]
    target_file = os.path.join(home, *paths2)
    shutil.copyfile(ini_file, target_file)

    res = modifyconfig_main(
        [
            "--ini_file",
            target_file,
            "--action",
            "SET",
            "--value",
            "123",
            "--section",
            "app:formshare",
            "--key",
            "test",
        ]
    )
    assert res == 1

    res = modifyconfig_main(
        [
            "--ini_file",
            target_file,
            "--action",
            "ADD",
            "--section",
            "app:formshare",
            "--key",
            "test",
        ]
    )
    assert res == 1

    res = modifyconfig_main(
        [
            "--ini_file",
            "/not_found.ini",
            "--action",
            "ADD",
            "--value",
            "123",
            "--section",
            "app:formshare",
            "--key",
            "test",
        ]
    )
    assert res == 1

    res = modifyconfig_main(
        [
            "--ini_file",
            target_file,
            "--action",
            "ADD",
            "--value",
            "123",
            "--section",
            "notExist",
            "--key",
            "test",
        ]
    )
    assert res == 1

    res = modifyconfig_main(
        [
            "--ini_file",
            target_file,
            "--action",
            "ADD",
            "--value",
            "123",
            "--section",
            "app:formshare",
            "--key",
            "test",
        ]
    )
    assert res == 0

    res = modifyconfig_main(
        [
            "--ini_file",
            target_file,
            "--action",
            "REMOVE",
            "--section",
            "app:formshare",
            "--key",
            "test",
        ]
    )
    assert res == 0
