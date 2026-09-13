"""The ElasticSearch export and import scripts, against the test cluster.

The export dumps the live indices to a directory. The import only ever
writes to indices named for this run, which are deleted at the end, so the
indices the rest of the suite reads are never touched.
"""

import os
import shutil
import uuid

from elasticsearch import Elasticsearch

from formshare.scripts.exportelasticsearch import main as export_indices
from formshare.scripts.importelasticsearch import main as import_indices

INDEX_GROUPS = ["user", "partner", "repository", "records"]


def t_e_s_t_es_scripts(test_object):
    config = test_object.server_config
    ini_file = config["global:config:file"]
    host = config["elasticsearch.user.host"]
    user = config["elasticsearch.user.name"]
    password = config["elasticsearch.user.password"]
    credentials = ["--user", user, "--password", password]
    index_names = [
        config["elasticsearch.{}.index_name".format(group)] for group in INDEX_GROUPS
    ]
    users_index = config["elasticsearch.user.index_name"]
    suffix = "_pytest_" + uuid.uuid4().hex[:6]
    created = []

    out_dir = os.path.join(test_object.working_dir, "es_dump" + suffix)
    all_dir = out_dir + "_all"
    empty_dir = out_dir + "_empty"
    os.makedirs(empty_dir)

    try:
        # An ini file that does not exist
        assert export_indices(["--ini", "/not/found.ini", "--output", out_dir]) == 1
        assert import_indices(["--ini", "/not/found.ini", "--input", out_dir]) == 1
        # A rename that is not old=new
        assert import_indices(["--rename", "nonsense", "--input", out_dir]) == 1
        # Nothing to import
        assert import_indices(["--ini", ini_file, "--input", "/no/such/dir"]) == 1
        assert import_indices(["--ini", ini_file, "--input", empty_dir]) == 1
        # A server that is not there. Port 9 refuses the connection at once
        assert export_indices(["--host", host, "--port", "9", "--output", out_dir]) == 1

        # The four indices the ini names, connection details from the ini
        assert (
            export_indices(["--ini", ini_file, "--output", out_dir, "--limit", "20"])
            == 0
        )
        assert os.path.isfile(os.path.join(out_dir, "manifest.json"))
        for name in index_names:
            assert os.path.isfile(os.path.join(out_dir, name + ".ndjson"))
            assert os.path.isfile(os.path.join(out_dir, name + ".mapping.json"))

        # TLS, a URL prefix and a CA bundle reach the client builder, and
        # the server behind them is not there either
        assert (
            export_indices(
                [
                    "--host",
                    host,
                    "--port",
                    "9",
                    "--scheme",
                    "https",
                    "--url-prefix",
                    "es",
                    "--no-verify-certs",
                    "--output",
                    out_dir,
                ]
            )
            == 1
        )
        assert (
            import_indices(
                [
                    "--host",
                    host,
                    "--port",
                    "9",
                    "--scheme",
                    "https",
                    "--url-prefix",
                    "es",
                    "--ca-certs",
                    ini_file,
                    "--input",
                    out_dir,
                ]
            )
            == 1
        )
        # An ini file without an app:formshare section falls back to the
        # first app: section, and one with no app: section to the defaults
        other_ini = os.path.join(out_dir, "other.ini")
        with open(other_ini, "w") as ini_handle:
            ini_handle.write("[app:other]\nelasticsearch.user.host = {}\n".format(host))
        bare_ini = os.path.join(out_dir, "bare.ini")
        with open(bare_ini, "w") as ini_handle:
            ini_handle.write("[server:main]\nport = 80\n")
        for an_ini in [other_ini, bare_ini]:
            assert (
                export_indices(["--ini", an_ini, "--port", "9", "--output", out_dir])
                == 1
            )
            assert (
                import_indices(["--ini", an_ini, "--port", "9", "--input", out_dir])
                == 1
            )

        # Indices named on the command line, one of them not on the server,
        # with the connection given by flags
        assert (
            export_indices(
                ["--host", host, "--port", "9200"]
                + credentials
                + [
                    "--index",
                    users_index,
                    "--index",
                    "formshare_no_such_index",
                    "--output",
                    out_dir,
                    "--limit",
                    "5",
                ]
            )
            == 0
        )

        # Every index on the cluster, one document each
        assert (
            export_indices(
                ["--ini", ini_file, "--all", "--output", all_dir, "--limit", "1"]
            )
            == 0
        )

        # Load the dump into indices of this run, created from the sidecars
        renames = []
        for name in index_names:
            renames = renames + ["--rename", "{0}={0}{1}".format(name, suffix)]
            created.append(name + suffix)
        assert (
            import_indices(
                ["--ini", ini_file, "--input", out_dir, "--replicas", "0", "--refresh"]
                + renames
            )
            == 0
        )
        # Again: the indices exist now, and --recreate drops them first
        assert (
            import_indices(
                ["--ini", ini_file, "--input", out_dir, "--recreate", "--limit", "3"]
                + renames
            )
            == 0
        )

        # One file into an index it is forced to, which exists by now
        users_file = os.path.join(out_dir, users_index + ".ndjson")
        assert (
            import_indices(
                [
                    "--ini",
                    ini_file,
                    "--file",
                    users_file,
                    "--index",
                    users_index + suffix,
                    "--limit",
                    "1",
                ]
            )
            == 0
        )

        # A file with no mapping sidecar into a new index: dynamic mapping
        no_sidecar = os.path.join(out_dir, "nosidecar" + suffix + ".ndjson")
        shutil.copy(users_file, no_sidecar)
        created.append("nosidecar" + suffix)
        assert (
            import_indices(
                [
                    "--ini",
                    ini_file,
                    "--file",
                    no_sidecar,
                    "--index",
                    "nosidecar" + suffix,
                    "--refresh",
                ]
            )
            == 0
        )

        # The same with creation switched off
        created.append("nocreate" + suffix)
        assert (
            import_indices(
                [
                    "--ini",
                    ini_file,
                    "--file",
                    no_sidecar,
                    "--index",
                    "nocreate" + suffix,
                    "--no-create",
                    "--refresh",
                ]
            )
            == 0
        )

        # A file that is not there is skipped
        assert (
            import_indices(["--ini", ini_file, "--file", "/no/such/file.ndjson"]) == 0
        )
    finally:
        client = Elasticsearch(
            "http://{}:9200".format(host), basic_auth=(user, password)
        )
        for name in created:
            client.indices.delete(index=name, ignore_unavailable=True)
        client.close()
        for a_dir in [out_dir, all_dir, empty_dir]:
            shutil.rmtree(a_dir, ignore_errors=True)
