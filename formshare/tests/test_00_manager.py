#!/usr/bin/env python
# -*- coding: utf-8 -*-


from formshare.start import start

from wsgiref.simple_server import make_server
import multiprocessing
import time


def test_pyramid_server():

    settings = {
        "pyramid.reload_templates": "true",
        "pyramid.debug_authorization": "false",
        "pyramid.debug_notfound": "false",
        "pyramid.debug_routematch": "false",
        "pyramid.default_locale_name": "en",
        "pyramid.includes": "\npyramid_debugtoolbar",
        "sqlalchemy.url": "mysql+mysqlconnector://root:72EkBqCs!@localhost/formshare?charset=utf8",
        "auth.main.secret": "WA&Vr-hfK8NE\\#38G",
        "auth.main.cookie": "formshare_main_auth_tkt",
        "auth.assistant.secret": "WA&Vr-hfK8NE\\#38G",
        "auth.assistant.cookie": "formshare_assistant_auth_tkt",
        "auth.secret": "WA&Vr-hfK8NE\\#38G",
        "aes.key": "!e[~faXa.kp&<wUM&C3NLG3?/pBv4hW&",
        "auth.opaque": "8ee0f2c2cbba476db0a8a81fcde4cbee",
        "auth.realm": "formshare@qlands.com",
        "auth.register_users_via_api": "false",
        "auth.register_users_via_web": "true",
        "auth.share_projects_among_users": "false",
        "auth.allow_guest_access": "false",
        "auth.allow_edit_profile_name": "true",
        "auth.allow_user_change_password": "true",
        "auth.auto_accept_collaboration": "false",
        "celery.broker": "amqp://formshare:formshare@localhost:5672/formshare",
        "celery.backend": "rpc://formshare:formshare@localhost:5672/formshare",
        "celery.taskname": "fstask",
        "elasticfeeds.feed_index": "formshare_feeds",
        "elasticfeeds.network_index": "formshare_network",
        "elasticsearch.user.index_name": "formshare_users",
        "elasticsearch.records.index_name": "formshare_records",
        "repository.path": "/home/cquiros/temp/formshare",
        "odktools.path": "/home/cquiros/odktools",
        "mysql.cnf": "/home/cquiros/data/projects2017/personal/software/FormShare/mysql.cnf",
        "mysql.host": "localhost",
        "mysql.port": "3306",
        "mysql.user": "root",
        "mysql.password": "72EkBqCs!",
        "mail.server.available": "true",
        "mail.server": "smtp.livemail.co.uk",
        "mail.port": "465",
        "mail.login": "noreply@qlands.com",
        "mail.password": "630vqSgKHVGTY4x22pxRvxp9Lua",
        "mail.starttls": "false",
        "mail.ssl": "true",
        "mail.from": "noreply@qlands.com",
        "mail.error": "formshare_support@qlands.com",
    }

    app = start(settings)
    server = make_server('127.0.0.1', 6543, app)
    server_process = multiprocessing.Process(target=server.serve_forever)
    server_process.start()
    time.sleep(15)
    # r = requests.get('http://127.0.0.1:6543/join')
    # print(r.status_code)

    server_process.terminate()
    server_process.join()
    del server_process
