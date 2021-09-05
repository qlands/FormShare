import logging

from formshare.views.classes import PartnerView, PartnerAPIView
from formshare.processes.db.partner import (
    get_projects_and_forms_by_partner,
    partner_has_project,
    partner_has_form,
)
from formshare.processes.db.form import (
    get_form_details,
    get_form_data,
    get_maintable_information,
    get_forms_for_schema,
)
from formshare.processes.db.project import get_project_id_from_name, get_project_details
import datetime
from pyramid.httpexceptions import HTTPNotFound
from formshare.processes.submission.api import (
    get_gps_points_from_form,
    get_fields_from_table,
    get_dataset_info_from_file,
    list_submission_media_files,
    get_submission_media_file,
)
from formshare.processes.elasticsearch.repository_index import (
    get_number_of_datasets_with_gps,
)
import mimetypes
from pyramid.response import FileResponse
import os
from formshare.products.products import get_form_products
from formshare.processes.db.products import get_product_output, update_download_counter
import formshare.plugins as p
from formshare.config.elasticfeeds import get_manager
from elasticfeeds.activity import Actor, Object, Activity


class PartnerForms(PartnerView):
    def process_view(self):
        return {
            "projects": get_projects_and_forms_by_partner(self.request, self.partnerID),
            "today": datetime.date.today(),
        }


class PartnerFormDetails(PartnerView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is None:
            raise HTTPNotFound

        partner_project = partner_has_project(self.request, self.partnerID, project_id)
        partner_form = partner_has_form(
            self.request, self.partnerID, project_id, form_id
        )

        if partner_project is None and partner_form is None:
            raise HTTPNotFound
        if partner_project is not None:
            if partner_project["time_bound"] == 1:
                if not (
                    partner_project["access_from"].date()
                    <= datetime.date.today()
                    <= partner_project["access_to"].date()
                ):
                    raise HTTPNotFound

        if partner_form is not None:
            if partner_form["time_bound"] == 1:
                if not (
                    partner_form["access_from"].date()
                    <= datetime.date.today()
                    <= partner_form["access_to"].date()
                ):
                    raise HTTPNotFound
        project_details = get_project_details(self.request, project_id)
        form_data = get_form_details(self.request, user_id, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        feed_manager = get_manager(self.request)
        actor = Actor(self.partner.id, "partner")
        feed_object = Object("{}|{}|{}".format(user_id, project_id, form_id), "form")
        activity = Activity(
            "access",
            actor,
            feed_object,
            extra={"remote_address": self.request.remote_addr},
        )
        try:
            feed_manager.add_activity_feed(activity)
        except Exception as e:
            logging.error(
                "Error: {} while registering "
                "activity for partner {} to form {}".format(
                    str(e), self.partner.email, project_id + "|" + form_id
                )
            )

        forms = get_forms_for_schema(self.request, form_data["form_schema"])
        number_with_gps = get_number_of_datasets_with_gps(
            self.request.registry.settings, project_id, forms
        )
        products = get_form_products(self.request, project_id, form_id)
        return {
            "formDetails": form_data,
            "projectDetails": project_details,
            "userid": user_id,
            "withgps": number_with_gps,
            "products": products,
        }


class PartnerDownloadGPSPoints(PartnerView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is None:
            raise HTTPNotFound

        partner_project = partner_has_project(self.request, self.partnerID, project_id)
        partner_form = partner_has_form(
            self.request, self.partnerID, project_id, form_id
        )

        if partner_project is None and partner_form is None:
            raise HTTPNotFound
        if partner_project is not None:
            if partner_project["time_bound"] == 1:
                if not (
                    partner_project["access_from"].date()
                    <= datetime.date.today()
                    <= partner_project["access_to"].date()
                ):
                    raise HTTPNotFound

        if partner_form is not None:
            if partner_form["time_bound"] == 1:
                if not (
                    partner_form["access_from"].date()
                    <= datetime.date.today()
                    <= partner_form["access_to"].date()
                ):
                    raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        created, data = get_gps_points_from_form(self.request, project_id, form_id)
        self.returnRawViewResult = True
        return data


class PartnerGetSubMissionInfo(PartnerView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        submission_id = self.request.matchdict["submissionid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is None:
            raise HTTPNotFound

        partner_project = partner_has_project(self.request, self.partnerID, project_id)
        partner_form = partner_has_form(
            self.request, self.partnerID, project_id, form_id
        )

        if partner_project is None and partner_form is None:
            raise HTTPNotFound
        if partner_project is not None:
            if partner_project["time_bound"] == 1:
                if not (
                    partner_project["access_from"].date()
                    <= datetime.date.today()
                    <= partner_project["access_to"].date()
                ):
                    raise HTTPNotFound

        if partner_form is not None:
            if partner_form["time_bound"] == 1:
                if not (
                    partner_form["access_from"].date()
                    <= datetime.date.today()
                    <= partner_form["access_to"].date()
                ):
                    raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)

        fields, checked = get_fields_from_table(
            self.request, project_id, form_id, "maintable", [], False
        )
        if form_data["form_schema"] is None:
            submission_info = get_dataset_info_from_file(
                self.request, project_id, form_id, submission_id
            )
        else:
            submission_info = get_maintable_information(
                self.request, project_id, form_id, submission_id
            )

        if submission_info is None:
            raise HTTPNotFound

        submission_data = []
        for key, value in submission_info.items():
            field_desc = None
            primary_key = False
            for a_field in fields:
                if form_data["form_schema"] is None:
                    if a_field["xmlcode"] == key:
                        field_desc = a_field["desc"]
                        if a_field["key"] == "true":
                            primary_key = True
                        break
                else:
                    if a_field["name"] == key:
                        field_desc = a_field["desc"]
                        if a_field["key"] == "true":
                            primary_key = True
                        break
            if field_desc is not None:
                submission_data.append(
                    {
                        "key": key,
                        "desc": field_desc,
                        "value": value,
                        "pkey": primary_key,
                    }
                )

        media_files = list_submission_media_files(
            self.request, project_id, form_id, submission_id
        )
        has_other_media = False
        for a_file in media_files:
            if not a_file["image"]:
                has_other_media = True
                break

        has_images = False
        for a_file in media_files:
            if a_file["image"]:
                has_images = True
                break

        return {
            "formData": form_data,
            "submissionData": submission_data,
            "submissionID": submission_id,
            "mediaFiles": media_files,
            "userid": user_id,
            "projcode": project_code,
            "formid": form_id,
            "submissionid": submission_id,
            "hasOtherMedia": has_other_media,
            "hasImages": has_images,
        }


class GetPartnerMediaFile(PartnerView):
    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        submission_id = self.request.matchdict["submissionid"]
        file_name = self.request.matchdict["filename"]
        thumbnail = self.request.params.get("thumbnail", None)
        if thumbnail is None:
            thumbnail = False
        else:
            thumbnail = True

        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is None:
            raise HTTPNotFound

        partner_project = partner_has_project(self.request, self.partnerID, project_id)
        partner_form = partner_has_form(
            self.request, self.partnerID, project_id, form_id
        )

        if partner_project is None and partner_form is None:
            raise HTTPNotFound
        if partner_project is not None:
            if partner_project["time_bound"] == 1:
                if not (
                    partner_project["access_from"].date()
                    <= datetime.date.today()
                    <= partner_project["access_to"].date()
                ):
                    raise HTTPNotFound

        if partner_form is not None:
            if partner_form["time_bound"] == 1:
                if not (
                    partner_form["access_from"].date()
                    <= datetime.date.today()
                    <= partner_form["access_to"].date()
                ):
                    raise HTTPNotFound

        file = get_submission_media_file(
            self.request, project_id, form_id, submission_id, file_name, thumbnail
        )
        if file is None:
            raise HTTPNotFound
        file_type = mimetypes.guess_type(file)[0]
        if file_type is None:
            file_type = "application/octet-stream"
        response = FileResponse(file, request=self.request, content_type=file_type)
        response.content_disposition = 'attachment; filename="' + os.path.basename(file)
        self.returnRawViewResult = True
        return response


class PartnerDownloadPrivateProduct(PartnerView):
    def __init__(self, request):
        PartnerView.__init__(self, request)
        self.checkCrossPost = False
        self.returnRawViewResult = True

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        product_id = self.request.matchdict["productid"]
        output_id = self.request.matchdict["outputid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is None:
            raise HTTPNotFound

        partner_project = partner_has_project(self.request, self.partnerID, project_id)
        partner_form = partner_has_form(
            self.request, self.partnerID, project_id, form_id
        )

        if partner_project is None and partner_form is None:
            raise HTTPNotFound
        if partner_project is not None:
            if partner_project["time_bound"] == 1:
                if not (
                    partner_project["access_from"].date()
                    <= datetime.date.today()
                    <= partner_project["access_to"].date()
                ):
                    raise HTTPNotFound

        if partner_form is not None:
            if partner_form["time_bound"] == 1:
                if not (
                    partner_form["access_from"].date()
                    <= datetime.date.today()
                    <= partner_form["access_to"].date()
                ):
                    raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        output_id, output_file, mime_type = get_product_output(
            self.request, project_id, form_id, product_id, output_id, False
        )
        if output_id is not None:
            continue_download = True
            # Load connected plugins and check if they modify the download process
            for plugin in p.PluginImplementations(p.IProduct):
                continue_download = plugin.before_partner_download_private_product(
                    self.request,
                    self.partnerID,
                    project_id,
                    form_id,
                    product_id,
                    output_id,
                    output_file,
                    mime_type,
                )
                break  # Only one plugging will be called to extend before_download_product
            if continue_download:
                feed_manager = get_manager(self.request)
                actor = Actor(self.partner.id, "partner")
                feed_object = Object(
                    "{}|{}|{}|{}|{}".format(
                        user_id, project_id, form_id, product_id, output_id
                    ),
                    "output",
                )
                activity = Activity(
                    "download",
                    actor,
                    feed_object,
                    extra={"remote_address": self.request.remote_addr},
                )
                try:
                    feed_manager.add_activity_feed(activity)
                except Exception as e:
                    logging.error(
                        "Error: {} while registering "
                        "activity for partner {} to form {}".format(
                            str(e), self.partner.email, project_id + "|" + form_id
                        )
                    )

                filename, file_extension = os.path.splitext(output_file)
                if file_extension == "":
                    file_extension = "unknown"
                response = FileResponse(
                    output_file, request=self.request, content_type=mime_type
                )
                response.content_disposition = (
                    'attachment; filename="' + form_id + file_extension + '"'
                )
                update_download_counter(
                    self.request, project_id, form_id, product_id, output_id
                )
                return response
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound


class PartnerDownloadPrivateProductByAPI(PartnerAPIView):
    def __init__(self, request):
        PartnerAPIView.__init__(self, request)

    def process_view(self):
        user_id = self.request.matchdict["userid"]
        project_code = self.request.matchdict["projcode"]
        form_id = self.request.matchdict["formid"]
        product_id = self.request.matchdict["productid"]
        output_id = self.request.matchdict["outputid"]
        project_id = get_project_id_from_name(self.request, user_id, project_code)
        if project_id is None:
            raise HTTPNotFound

        partner_project = partner_has_project(self.request, self.partnerID, project_id)
        partner_form = partner_has_form(
            self.request, self.partnerID, project_id, form_id
        )

        if partner_project is None and partner_form is None:
            raise HTTPNotFound
        if partner_project is not None:
            if partner_project["time_bound"] == 1:
                if not (
                    partner_project["access_from"].date()
                    <= datetime.date.today()
                    <= partner_project["access_to"].date()
                ):
                    raise HTTPNotFound

        if partner_form is not None:
            if partner_form["time_bound"] == 1:
                if not (
                    partner_form["access_from"].date()
                    <= datetime.date.today()
                    <= partner_form["access_to"].date()
                ):
                    raise HTTPNotFound

        form_data = get_form_data(self.request, project_id, form_id)
        if form_data is None:
            raise HTTPNotFound

        output_id, output_file, mime_type = get_product_output(
            self.request, project_id, form_id, product_id, output_id, False
        )
        if output_id is not None:
            continue_download = True
            # Load connected plugins and check if they modify the download process
            for plugin in p.PluginImplementations(p.IProduct):
                continue_download = plugin.before_partner_download_product_by_api(
                    self.request,
                    self.partnerID,
                    project_id,
                    form_id,
                    product_id,
                    output_id,
                    output_file,
                    mime_type,
                )
                break  # Only one plugging will be called to extend before_download_product
            if continue_download:

                feed_manager = get_manager(self.request)
                actor = Actor(self.partnerID, "partner")
                feed_object = Object(
                    "{}|{}|{}|{}|{}".format(
                        user_id, project_id, form_id, product_id, output_id
                    ),
                    "output",
                )
                activity = Activity(
                    "download",
                    actor,
                    feed_object,
                    extra={"remote_address": self.request.remote_addr},
                )
                try:
                    feed_manager.add_activity_feed(activity)
                except Exception as e:
                    logging.error(
                        "Error: {} while registering "
                        "activity for partner {} to form {}".format(
                            str(e), self.partner.email, project_id + "|" + form_id
                        )
                    )

                filename, file_extension = os.path.splitext(output_file)
                if file_extension == "":
                    file_extension = "unknown"
                response = FileResponse(
                    output_file, request=self.request, content_type=mime_type
                )
                response.content_disposition = (
                    'attachment; filename="' + form_id + file_extension + '"'
                )
                update_download_counter(
                    self.request, project_id, form_id, product_id, output_id
                )
                return response
            else:
                raise HTTPNotFound
        else:
            raise HTTPNotFound
