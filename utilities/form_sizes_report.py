#!/usr/bin/env python3
"""Generate an Excel report of form sizes (submissions + products) per form."""

import argparse
import configparser
import os
from pathlib import Path

import openpyxl
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from formshare.models.formshare import Odkform, Product, Project, User, Userproject


def dir_size_bytes(path: Path) -> int:
    if not path.exists():
        return 0
    total = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = Path(root) / f
            try:
                total += fp.stat().st_size
            except OSError:
                pass
    return total


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--ini",
        default="/home/cquiros/data/projects2017/personal/software/FormShare/development.ini",
    )
    parser.add_argument("--output", default="form_sizes.xlsx")
    args = parser.parse_args()

    cfg = configparser.ConfigParser()
    cfg.read(args.ini)
    section = "app:formshare" if cfg.has_section("app:formshare") else "app:main"
    db_url = cfg.get(section, "sqlalchemy.url")
    repo_path = cfg.get(section, "repository.path")

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    rows = (
        session.query(
            User.user_id,
            Project.project_name,
            Odkform.form_name,
            Odkform.project_id,
            Odkform.form_id,
            Odkform.form_directory,
        )
        .join(Userproject, Userproject.user_id == User.user_id)
        .join(Project, Project.project_id == Userproject.project_id)
        .join(Odkform, Odkform.project_id == Project.project_id)
        .filter(Userproject.access_type == 1)
        .all()
    )

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Form sizes"
    ws.append(["user_id", "project_name", "form_name", "size in MB"])

    for user_id, project_name, form_name, project_id, form_id, form_directory in rows:
        size = 0
        if form_directory:
            sub_dir = Path(repo_path) / "odk" / "forms" / form_directory / "submissions"
            size += dir_size_bytes(sub_dir)

        products = (
            session.query(Product.output_file)
            .filter(Product.project_id == project_id, Product.form_id == form_id)
            .all()
        )
        for (output_file,) in products:
            if output_file and os.path.isfile(output_file):
                try:
                    size += os.path.getsize(output_file)
                except OSError:
                    pass

        ws.append([user_id, project_name, form_name, round(size / (1024 * 1024), 3)])

    wb.save(args.output)
    print(f"Wrote {args.output} with {ws.max_row - 1} rows")


if __name__ == "__main__":
    main()
