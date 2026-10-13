"""The public half of a project's encryption key, for those who seal.

Field encryption (docs/formshare_field_encryption/, formshare.md 7.4): an
answer to a marked question may be sealed before it reaches FormShare -- by an
API client pushing JSON, by a device -- and the envelope is stored as it is.
To seal, the client needs the project's public key. A public key needs no
protection, but only someone who works with the project is told about it: a
user with access to it, or one of its assistants. Every version comes too, so
that a client can tell which key an envelope it holds was sealed with.
"""

from formshare.middleware.httpexceptions import HTTPNotFound
from formshare.processes.db import get_project_access_type, get_project_id_from_name
from formshare.processes.db.encryption import get_project_keys
from formshare.views.classes import AssistantView, PrivateView


def project_keys_document(request, project_id):
    """{"project_id", "public_key": the one to seal with, or None, "keys":
    every version, oldest first}. Each version carries its signing key and
    the signature of the version that vouched for it (README 3.6), so that a
    client which knows the project's first key id can check that the key it
    seals with descends from it."""
    keys = get_project_keys(request, project_id)
    active = [a_key["public_key"] for a_key in keys if a_key["key_status"] == "active"]
    return {
        "project_id": project_id,
        "public_key": active[0] if active else None,
        "keys": [
            {
                "key_id": a_key["key_id"],
                "public_key": a_key["public_key"],
                "key_status": a_key["key_status"],
                "sign_public_key": a_key["sign_public_key"],
                "signed_by": a_key["signed_by"],
                "key_signature": a_key["key_signature"],
            }
            for a_key in keys
        ],
    }


class ProjectEncryptionKeysView(PrivateView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is None:
            raise HTTPNotFound
        access_type = get_project_access_type(
            self.request, project_id, user_id, self.user.login
        )
        if access_type > 4:
            raise HTTPNotFound
        self.returnRawViewResult = True
        return project_keys_document(self.request, project_id)


class AssistantEncryptionKeysView(AssistantView):
    def process_view(self):
        self.returnRawViewResult = True
        return project_keys_document(self.request, self.projectID)
