import os
from jinja2 import Environment, FileSystemLoader
import argparse


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "fluent_conf_file", help="Path to fluent configuration file to create"
    )
    parser.add_argument("--formshare_path", required=True, help="Path to FormShare")
    parser.add_argument(
        "--formshare_log_file", required=True, help="Path to FormShare log file to read"
    )
    parser.add_argument(
        "--elastic_search_host", required=True, help="ElasticSearch host name"
    )
    parser.add_argument(
        "--elastic_search_port", required=True, help="ElasticSearch host name"
    )
    parser.add_argument(
        "--elastic_search_ssl", action="store_true", help="ElasticSearch use SSL"
    )

    args = parser.parse_args()

    template_environment = Environment(
        autoescape=False,
        loader=FileSystemLoader(os.path.join(args.formshare_path, "templates")),
        trim_blocks=False,
    )
    context = {
        "elastic_search_host": args.elastic_search_host,
        "elastic_search_port": args.elastic_search_port,
        "elastic_search_ssl": args.elastic_search_ssl,
        "formshare_log_file": args.formshare_log_file,
    }

    rendered_template = template_environment.get_template("fluent.jinja2").render(
        context
    )

    with open(args.fluent_conf_file, "w") as f:
        f.write(rendered_template)
