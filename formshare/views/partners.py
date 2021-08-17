from formshare.views.classes import PrivateView
from pyramid.httpexceptions import HTTPNotFound, HTTPFound
import validators
from formshare.processes.db.partner import partner_exists, register_partner
from formshare.config.encdecdata import encode_data
import datetime
import uuid
import formshare.plugins as p
from formshare.processes.elasticsearch.partner_index import get_partner_index_manager


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
