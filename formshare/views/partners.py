from formshare.views.classes import PrivateView
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
import validators
from formshare.processes.db.partner import (
    partner_exists,
    register_partner,
    get_partner_details,
    partner_email_exists,
    update_partner,
    update_partner_password,
    delete_partner,
)
from formshare.processes.db.user import get_user_details
from formshare.config.encdecdata import encode_data
import datetime
import uuid
import formshare.plugins as p
from formshare.processes.elasticsearch.partner_index import get_partner_index_manager
import logging


log = logging.getLogger("formshare")


class PartnersListView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.set_active_menu("partners")

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        if self.user.id != user_id:
            raise HTTPNotFound
        return {"userid": user_id}


class AddPartnerView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.set_active_menu("partners")

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        if self.user.id != user_id:
            raise HTTPNotFound

        partner_details = {}
        if self.request.method == "POST":
            partner_details = self.get_post_dict()
            partner_details["partner_email"] = partner_details["partner_email"].lower()
            email_valid = validators.email(partner_details["partner_email"])
            if email_valid:
                if not partner_exists(self.request, partner_details["partner_email"]):
                    if partner_details["partner_password"] != "":
                        if (
                            partner_details["partner_password"]
                            == partner_details["partner_password2"]
                        ):
                            encoded_password = encode_data(
                                self.request, partner_details["partner_password"]
                            )
                            if partner_details["partner_organization"] == "":
                                self.append_to_errors(
                                    self._("The organization cannot be empty")
                                )
                                return {
                                    "partnerData": partner_details,
                                    "userid": user_id,
                                }
                            if partner_details["partner_name"] == "":
                                self.append_to_errors(
                                    self._("The name cannot be empty")
                                )
                                return {
                                    "partnerData": partner_details,
                                    "userid": user_id,
                                }
                            if partner_details["partner_telephone"] == "":
                                self.append_to_errors(
                                    self._(
                                        "The partner telephone contact cannot be empty"
                                    )
                                )
                                return {
                                    "partnerData": partner_details,
                                    "userid": user_id,
                                }

                            partner_details["partner_password"] = encoded_password
                            partner_details.pop("partner_password2", None)
                            partner_details["partner_cdate"] = datetime.datetime.now()
                            partner_details["partner_apikey"] = str(uuid.uuid4())
                            partner_details["partner_id"] = str(uuid.uuid4())
                            partner_details["created_by"] = user_id
                            continue_creation = True
                            for plugin in p.PluginImplementations(p.IPartner):
                                (
                                    data,
                                    continue_creation,
                                    error_message,
                                ) = plugin.before_create(self.request, partner_details)
                                if not continue_creation:
                                    self.append_to_errors(error_message)
                                else:
                                    partner_details = data
                                break  # Only one plugging will be called to extend before_create
                            if continue_creation:
                                added, error_message = register_partner(
                                    self.request, partner_details
                                )
                                if not added:
                                    self.append_to_errors(error_message)
                                else:
                                    # Add the partner to the partner index
                                    partner_index = get_partner_index_manager(
                                        self.request
                                    )
                                    partner_index_data = partner_details
                                    partner_index_data.pop("partner_apikey", None)
                                    partner_index_data.pop("partner_password", None)
                                    partner_index_data.pop("partner_cdate", None)
                                    partner_index_data.pop("partner_telephone", None)
                                    partner_index_data.pop("csrf_token", None)
                                    partner_index.add_partner(
                                        partner_details["partner_id"],
                                        partner_index_data,
                                    )
                                    next_page = self.request.route_url(
                                        "manage_partners", userid=user_id
                                    )
                                    for plugin in p.PluginImplementations(p.IPartner):
                                        plugin.after_create(
                                            self.request, partner_details
                                        )
                                    log.error(
                                        "The user {} created the partner {}".format(
                                            self.userID, partner_details["partner_id"]
                                        )
                                    )
                                    self.request.session.flash(
                                        self._("The partner was added successfully")
                                    )
                                    self.returnRawViewResult = True
                                    return HTTPFound(location=next_page)
                        else:
                            self.append_to_errors(
                                self._(
                                    "The password and its confirmation are not the same"
                                )
                            )
                    else:
                        self.append_to_errors(self._("The password cannot be empty"))
                else:
                    self.append_to_errors(
                        self._("This partner email address already exist")
                    )
            else:
                self.append_to_errors(self._("The email you provided is invalid"))

        return {"userid": user_id, "partnerData": partner_details}


class EditPartnerView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.set_active_menu("partners")

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        partner_to_modify = self.request.matchdict["partnerid"]
        if self.user.id != user_id:
            raise HTTPNotFound

        partner_details = get_partner_details(self.request, partner_to_modify)
        partner_details["by_details"] = get_user_details(
            self.request, partner_details["created_by"]
        )
        if not partner_details:
            raise HTTPNotFound
        if self.request.method == "POST":
            if partner_details["created_by"] != user_id:
                if self.user.super != 1:
                    raise HTTPNotFound

            partner_data = self.get_post_dict()
            if "modify" in partner_data.keys():

                if partner_data["partner_organization"] == "":
                    self.append_to_errors(self._("The organization cannot be empty"))
                    return {
                        "partnerData": partner_details,
                        "userid": user_id,
                    }
                if partner_data["partner_name"] == "":
                    self.append_to_errors(self._("The name cannot be empty"))
                    return {
                        "partnerData": partner_details,
                        "userid": user_id,
                    }
                if partner_data["partner_telephone"] == "":
                    self.append_to_errors(
                        self._("The partner telephone contact cannot be empty")
                    )
                    return {
                        "partnerData": partner_details,
                        "userid": user_id,
                    }

                email_valid = validators.email(partner_data["partner_email"])
                if not email_valid:
                    self.append_to_errors(self._("This email address is not valid"))
                else:
                    if partner_email_exists(
                        self.request, partner_to_modify, partner_data["partner_email"]
                    ):
                        self.append_to_errors(
                            self._(
                                "This email address already belongs to another partner"
                            )
                        )
                    else:
                        if (
                            partner_data["partner_apikey"]
                            != partner_details["partner_apikey"]
                        ):
                            log.warning(
                                "User {} changed the API key of partner {} from {} to {}".format(
                                    user_id,
                                    partner_to_modify,
                                    partner_details["partner_apikey"],
                                    partner_data["partner_apikey"],
                                )
                            )
                        continue_edit = True
                        for plugin in p.PluginImplementations(p.IPartner):
                            (data, continue_edit, error_message,) = plugin.before_edit(
                                self.request, partner_to_modify, partner_data
                            )
                            if not continue_edit:
                                self.append_to_errors(error_message)
                            else:
                                partner_details = data
                            break  # Only one plugging will be called to extend before_create
                        if continue_edit:
                            res, message = update_partner(
                                self.request, partner_to_modify, partner_data
                            )
                            if res:
                                for plugin in p.PluginImplementations(p.IPartner):
                                    plugin.after_edit(
                                        self.request,
                                        partner_to_modify,
                                        partner_data,
                                    )

                                partner_index = get_partner_index_manager(self.request)
                                partner_index_data = partner_data
                                partner_index_data.pop("partner_apikey", None)
                                partner_index_data.pop("csrf_token", None)
                                partner_index_data.pop("modify", None)

                                partner_index.update_partner(
                                    partner_to_modify, partner_index_data
                                )
                                log.error(
                                    "The user {} modified the partner {}".format(
                                        self.userID, partner_details["partner_id"]
                                    )
                                )
                                self.request.session.flash(
                                    self._("The partner has been updated")
                                )
                                self.returnRawViewResult = True
                                return HTTPFound(
                                    location=self.request.route_url(
                                        "manage_partners", userid=user_id
                                    )
                                )
                            else:
                                self.append_to_errors(message)

            if "changepass" in partner_data.keys():
                if partner_data["partner_password"] != "":
                    if (
                        partner_data["partner_password"]
                        == partner_data["partner_password2"]
                    ):
                        encoded_password = encode_data(
                            self.request, partner_data["partner_password"]
                        )
                        updated, message = update_partner_password(
                            self.request, partner_to_modify, encoded_password
                        )
                        if updated:
                            log.warning(
                                "Tha user {} changed the password for partner {}".format(
                                    user_id, partner_to_modify
                                )
                            )
                            self.returnRawViewResult = True
                            self.request.session.flash(
                                self._(
                                    "The password for {} was modified".format(
                                        partner_details["partner_name"]
                                    )
                                )
                            )
                            return HTTPFound(
                                location=self.request.route_url(
                                    "manage_partners", userid=user_id
                                )
                            )
                        else:
                            self.append_to_errors(message)
                    else:
                        self.append_to_errors(
                            self._("The password and its confirmation are not the same")
                        )
                else:
                    self.append_to_errors(self._("The password cannot be empty"))
        return {"userid": user_id, "partnerData": partner_details}


class DeletePartnerView(PrivateView):
    def __init__(self, request):
        PrivateView.__init__(self, request)
        self.privateOnly = True
        self.set_active_menu("partners")
        self.checkCrossPost = False

    def process_view(self):
        if self.request.method == "GET":
            raise HTTPNotFound
        else:
            user_id = self.request.matchdict["userid"]
            partner_to_delete = self.request.matchdict["partnerid"]
            if self.user.id != user_id:
                raise HTTPNotFound

            partner_details = get_partner_details(self.request, partner_to_delete)
            if not partner_details:
                raise HTTPNotFound
            by_details = get_user_details(self.request, partner_details["created_by"])
            if partner_details["created_by"] != user_id:
                if self.user.super != 1:
                    self.returnRawViewResult = True
                    self.add_error(
                        self._(
                            "This partner was created by {0} ({1}). "
                            "Only {0} or and administrator can delete it".format(
                                by_details["user_name"], by_details["user_email"]
                            )
                        )
                    )
                    return HTTPFound(
                        location=self.request.route_url(
                            "manage_partners", userid=user_id
                        )
                    )
            continue_delete = True
            for plugin in p.PluginImplementations(p.IPartner):
                (continue_delete, error_message,) = plugin.before_delete(
                    self.request, partner_to_delete, partner_details
                )
                if not continue_delete:
                    self.add_error(error_message)
                    self.returnRawViewResult = True
                    return HTTPFound(
                        location=self.request.route_url(
                            "manage_partners", userid=user_id
                        )
                    )
                break  # Only one plugging will be called to extend before_create
            if continue_delete:
                deleted, error_message = delete_partner(self.request, partner_to_delete)
                if deleted:
                    for plugin in p.PluginImplementations(p.IPartner):
                        plugin.after_delete(
                            self.request,
                            partner_to_delete,
                        )

                    partner_index = get_partner_index_manager(self.request)
                    partner_index.remove_partner(partner_to_delete)
                    log.error(
                        "The user {} deleted the partner {}".format(
                            self.userID, partner_to_delete
                        )
                    )
                    self.request.session.flash(self._("The partner has been deleted"))
                    self.returnRawViewResult = True
                    return HTTPFound(
                        location=self.request.route_url(
                            "manage_partners", userid=user_id
                        )
                    )
                else:
                    self.add_error(error_message)
                    self.returnRawViewResult = True
                    return HTTPFound(
                        location=self.request.route_url(
                            "manage_partners", userid=user_id
                        )
                    )
