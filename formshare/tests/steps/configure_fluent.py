import os


def t_e_s_t_configure_fluent():
    from formshare.scripts.configurefluent import main as configurefluent_main
    from pathlib import Path

    here = os.path.dirname(os.path.abspath(__file__)).split("/formshare/tests")[0]

    home = str(Path.home())
    paths2 = ["fluent.ini"]
    fluent_file = os.path.join(home, *paths2)

    res = configurefluent_main(
        [
            "--formshare_path",
            here,
            "--formshare_log_file",
            "log.ini",
            "--elastic_search_host",
            "localhost",
            "--elastic_search_port",
            "9200",
            fluent_file,
        ]
    )
    assert res == 0
    assert os.path.exists(fluent_file)
