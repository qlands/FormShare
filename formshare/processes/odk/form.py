import uuid
import os
import shutil
from lxml import etree
from pyxform import xls2xform
from formshare.models import Odkform as Form
from formshare.models import map_to_schema
import datetime
import json
from hashlib import md5
import logging
import sys
from sqlalchemy.exc import IntegrityError

__all__ = ['upload_odk_form']

log = logging.getLogger(__name__)


def upload_odk_form(request, project_id, user_id, odk_dir, form_data):
    uid = str(uuid.uuid4())
    form_directory = uid[-12:]
    paths = ['tmp', uid]
    os.makedirs(os.path.join(odk_dir, *paths))

    input_file = request.POST['xlsx'].file
    input_file_name = request.POST['xlsx'].filename

    paths = ['tmp', uid, input_file_name]
    file_name = os.path.join(odk_dir, *paths)

    input_file.seek(0)
    with open(file_name, 'wb') as permanent_file:
        shutil.copyfileobj(input_file, permanent_file)

    input_file.close()

    parts = os.path.splitext(input_file_name)

    paths = ['tmp', uid, parts[0]+'.xml']
    xml_file = os.path.join(odk_dir, *paths)

    try:
        xls2xform.xls2xform_convert(file_name, xml_file)

        # Check if the conversion created itemsets.csv
        output_dir = os.path.split(xml_file)[0]
        itemsets_csv = os.path.join(output_dir, "itemsets.csv")
        if not os.path.isfile(itemsets_csv):
            itemsets_csv = ""

        tree = etree.parse(xml_file)
        root = tree.getroot()
        nsmap = root.nsmap[None]
        h_nsmap = root.nsmap['h']
        eid = root.findall(".//{" + nsmap + "}" + parts[0])
        if eid:
            form_id = eid[0].get("id")
            form_title = root.findall(".//{" + h_nsmap + "}title")
            res = request.dbsession.query(Form).filter(Form.form_id == form_id).filter(
                Form.project_id == project_id).first()
            if res is None:
                paths = ['forms', form_directory, 'media']
                if not os.path.exists(os.path.join(odk_dir, *paths)):
                    os.makedirs(os.path.join(odk_dir, *paths))

                    paths = ['forms', form_directory, 'submissions']
                    os.makedirs(os.path.join(odk_dir, *paths))

                    paths = ['forms', form_directory, 'submissions', 'logs']
                    os.makedirs(os.path.join(odk_dir, *paths))

                    paths = ['forms', form_directory, 'submissions', 'maps']
                    os.makedirs(os.path.join(odk_dir, *paths))

                    paths = ['forms', form_directory, 'repository']
                    os.makedirs(os.path.join(odk_dir, *paths))
                    paths = ['forms', form_directory, 'repository', 'temp']
                    os.makedirs(os.path.join(odk_dir, *paths))

                xls_file_fame = os.path.basename(file_name)
                xml_file_name = os.path.basename(xml_file)
                paths = ['forms', form_directory, xls_file_fame]
                final_xls = os.path.join(odk_dir, *paths)
                paths = ['forms', form_directory, xml_file_name]
                final_xml = os.path.join(odk_dir, *paths)
                shutil.copyfile(file_name, final_xls)
                shutil.copyfile(xml_file, final_xml)

                form_data['project_id'] = project_id
                form_data['form_id'] = form_id
                form_data['form_name'] = form_title[0].text
                form_data['form_cdate'] = datetime.datetime.now()
                form_data['form_directory'] = form_directory
                form_data['form_accsub'] = 1
                form_data['form_testing'] = 1
                form_data['form_xlsfile'] = final_xls
                form_data['form_xmlfile'] = final_xml
                form_data['form_pubby'] = user_id

                mapped_data = map_to_schema(Form, form_data)
                new_form = Form(**mapped_data)
                try:
                    request.dbsession.add(new_form)
                    request.dbsession.flush()
                except IntegrityError as e:
                    request.dbsession.rollback()
                    return False, str(e)
                except RuntimeError:
                    request.dbsession.rollback()
                    return False, sys.exc_info()[0]

                # If we have itemsets.csv add it to the media path
                if itemsets_csv != "":
                    paths = ['forms', form_directory, 'media', 'itemsets.csv']
                    itemset_file = os.path.join(odk_dir, *paths)
                    shutil.copyfile(itemsets_csv, itemset_file)

                paths = ['forms', form_directory, parts[0]+".json"]
                json_file = os.path.join(odk_dir, *paths)

                metadata = {"formID": form_id, "name": form_title[0].text, "majorMinorVersion": "",
                            "version": datetime.datetime.now().strftime("%Y%m%d"),
                            "hash": 'md5:' + md5(open(final_xml, 'rb').read()).hexdigest(),
                            "descriptionText": form_title[0].text}

                with open(json_file, "w",) as outfile:
                    json_string = json.dumps(metadata, indent=4, ensure_ascii=False)
                    outfile.write(json_string)
                    return True, form_id
            else:
                return False, request.translate("Form already exists in this project")
        else:
            return False, request.translate(
                "Cannot find XForm ID. Please send this form to support_formshare@qlands.com")

    except RuntimeError:
        log.error("Error {} while adding form {} in project {}".format(sys.exc_info()[0], input_file_name, project_id))
        return False, sys.exc_info()[0]
