from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool


def store_task_status(task, config):
    from sqlalchemy import create_engine

    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    engine.execute(
        "INSERT INTO finishedtask (task_id,task_enumber) VALUES ('{}',0)".format(task)
    )


def get_form_details(config, project, form):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    result = engine.execute(
        "SELECT form_directory,form_schema,form_reptask,form_createxmlfile,form_insertxmlfile,form_hexcolor,form_pkey "
        "FROM odkform WHERE project_id = '{}' AND form_id = '{}'".format(project, form)
    ).fetchone()
    result = {
        "form_directory": result[0],
        "form_schema": result[1],
        "form_reptask": result[2],
        "form_createxmlfile": result[3],
        "form_insertxmlfile": result[4],
        "form_hexcolor": result[5],
        "form_pkey": result[6],
    }
    engine.dispose()
    return result


def get_repository_task(config, project, form):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    result = engine.execute(
        "SELECT celery_taskid FROM product WHERE project_id = '{}' "
        "AND form_id = '{}' AND product_id = 'repository'".format(project, form)
    ).fetchone()
    res = result[0]
    engine.dispose()
    return res


def get_one_submission(config, form_schema):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    result = engine.execute(
        "SELECT surveyid FROM {}.maintable".format(form_schema)
    ).fetchone()
    result = result[0]
    engine.dispose()
    return result


def get_partner_api_key(config, partner_id):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    result = engine.execute(
        "SELECT partner_apikey FROM formshare.partner WHERE partner_id='{}'".format(
            partner_id
        )
    ).fetchone()
    result = result[0]
    engine.dispose()
    return result


def get_last_task(config, project_id, form_id, product_id):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    sql = (
        "SELECT celery_taskid FROM product "
        "WHERE project_id = '{}' "
        "AND form_id = '{}' "
        "AND product_id = '{}' "
        "ORDER BY datetime_added DESC LIMIT 1".format(project_id, form_id, product_id)
    )
    result = engine.execute(sql).fetchone()
    result = result[0]
    engine.dispose()
    return result


def get_tokens_from_user(config, user_email):
    engine = create_engine(config["sqlalchemy.url"], poolclass=NullPool)
    sql = (
        "SELECT user_password_reset_key,user_password_reset_token,user_password_reset_expires_on "
        "FROM fsuser where user_email = '{}'".format(user_email)
    )
    result = engine.execute(sql).fetchone()
    return {
        "user_password_reset_key": result[0],
        "user_password_reset_token": result[1],
        "user_password_reset_expires_on": result[2],
    }
