import json
import secrets
from datetime import datetime

from dateutil.relativedelta import relativedelta
from pyramid.response import Response

from formshare.models import User, Collaborator
from formshare.processes.email.send_email import send_token_email


class TokenView(object):
    def __init__(self, request):
        self.request = request
        self._ = self.request.translate

    def __call__(self):
        if self.request.method != "POST":
            response = Response(
                content_type="application/json",
                status=400,
                body=json.dumps(
                    {
                        "status": "400",
                        "error": self._("Tokens can only be requested by POST."),
                    }
                ).encode(),
            )
            return response
        else:
            api_key = self.request.POST.get("X-API-Key", None)
            api_secret = self.request.POST.get("X-API-Secret", None)
            if api_key is None and api_secret is None:
                try:
                    json_data = json.loads(self.request.body)
                    api_key = json_data.get("X-API-Key", None)
                    api_secret = json_data.get("X-API-Secret", None)
                except:
                    pass

            if api_key is not None and api_secret is not None:
                res = (
                    self.request.dbsession.query(User)
                    .filter(User.user_apikey == api_key)
                    .filter(User.user_apisecret == api_secret)
                    .filter(User.user_active == 1)
                    .first()
                )
                if res is not None:
                    token = secrets.token_hex(16)
                    token_expires_on = datetime.now() + relativedelta(hours=+24)
                    self.request.dbsession.query(User).filter(
                        User.user_apikey == api_key
                    ).update(
                        {
                            "user_apitoken": token,
                            "user_apitoken_expires_on": token_expires_on,
                        }
                    )
                    send_token_email(self.request, res.user_email, token_expires_on)
                    response = Response(
                        content_type="application/json",
                        status=200,
                        body=json.dumps(
                            {
                                "status": "200",
                                "result": {
                                    "token": token,
                                    "expires_on": token_expires_on,
                                },
                            },
                            indent=4,
                            default=str,
                        ).encode(),
                    )
                    return response
                res = (
                    self.request.dbsession.query(Collaborator)
                    .filter(Collaborator.coll_apikey == api_key)
                    .filter(Collaborator.coll_apisecret == api_secret)
                    .filter(Collaborator.coll_active == 1)
                    .first()
                )
                if res is not None:
                    token = secrets.token_hex(16)
                    token_expires_on = datetime.now() + relativedelta(hours=+24)
                    self.request.dbsession.query(Collaborator).filter(
                        Collaborator.coll_apikey == api_key
                    ).filter(Collaborator.coll_active == 1).update(
                        {
                            "coll_apitoken": token,
                            "coll_apitoken_expires_on": token_expires_on,
                        }
                    )
                    send_token_email(self.request, res.coll_email, token_expires_on)
                    response = Response(
                        content_type="application/json",
                        status=200,
                        body=json.dumps(
                            {
                                "status": "200",
                                "result": {
                                    "token": token,
                                    "expires_on": token_expires_on,
                                },
                            },
                            indent=4,
                            default=str,
                        ).encode(),
                    )
                    return response

                response = Response(
                    content_type="application/json",
                    status=401,
                    body=json.dumps(
                        {
                            "status": "401",
                            "error": self._("Such API key does not exist."),
                        }
                    ).encode(),
                )
                return response

            else:
                response = Response(
                    content_type="application/json",
                    status=400,
                    body=json.dumps(
                        {
                            "status": "400",
                            "error": self._(
                                "You need to indicate an API key (X-API-Key) and an API Secret (X-API-Secret)."
                            ),
                        }
                    ).encode(),
                )
                return response
